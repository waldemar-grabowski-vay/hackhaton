// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

use std::collections::{BTreeMap, HashMap};
use std::sync::Arc;

use tokio::sync::mpsc::UnboundedSender;
use tokio::task::JoinSet;

use ree_debug_engine::checks::{all_checks, Category, CheckResult, Outcome};
use ree_debug_engine::inventory::{load_default, Host, HostKind};
use ree_debug_engine::ping::{self, PingStatus, PingUpdate};
use crate::repair::{self, RepairAction, RepairKind, RepairStep};
use ree_debug_engine::ssh::SshTarget;

pub struct App {
    pub stage: Stage,
}

pub enum Stage {
    Menu(Menu),
    Picking(Picker),
    Guides(GuidesView),
    Dashboard(Dashboard),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MenuEntry {
    Debug,
    Guides,
}

impl MenuEntry {
    pub const ALL: [MenuEntry; 2] = [MenuEntry::Debug, MenuEntry::Guides];

    pub fn label(self) -> &'static str {
        match self {
            MenuEntry::Debug => "Debug a testbed",
            MenuEntry::Guides => "Open repair guides",
        }
    }

    pub fn detail(self) -> &'static str {
        match self {
            MenuEntry::Debug => "Pick a TS or VE host and run all checks against it.",
            MenuEntry::Guides => "Browse repair playbooks (XCP, etc.) without connecting to a host.",
        }
    }
}

pub struct Menu {
    pub cursor: usize,
}

impl Menu {
    fn new() -> Self {
        Self { cursor: 0 }
    }

    pub fn entries(&self) -> &'static [MenuEntry] {
        &MenuEntry::ALL
    }

    pub fn selected(&self) -> MenuEntry {
        MenuEntry::ALL[self.cursor.min(MenuEntry::ALL.len() - 1)]
    }
}

/// Position in the guides walkthrough. Maps onto a flat sequence:
/// step 0 header → step 0 sub-checks → step 1 header → step 1 sub-checks → …
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GuidesTarget {
    pub step: usize,
    /// `None` = step header is selected. `Some(i)` = sub-check `i` selected.
    pub sub: Option<usize>,
}

pub struct GuidesView {
    pub kind: RepairKind,
    pub flavor: HostKind,
    pub steps: Vec<RepairStep>,
    /// Flat index into the cursor target list (step header or sub-check).
    pub cursor: usize,
    /// Some when reached via menu → host picker; commands run over SSH against
    /// this host. None for browse-only reference mode (Enter is a no-op).
    pub host: Option<String>,
    pub running_step: Option<usize>,
    /// Top-level status per step.
    pub status: Vec<Option<RepairStatus>>,
    /// Sub-check status: `sub_status[step][sub]`.
    pub sub_status: Vec<Vec<Option<RepairStatus>>>,
}

impl GuidesView {
    fn new() -> Self {
        let kind = RepairKind::Xcp;
        let flavor = HostKind::Ts;
        let steps = repair::steps_for(kind, flavor);
        let (status, sub_status) = init_status(&steps);
        Self {
            kind,
            flavor,
            steps,
            cursor: 0,
            host: None,
            running_step: None,
            status,
            sub_status,
        }
    }

    fn for_host(host: &Host) -> Self {
        let kind = RepairKind::Xcp;
        let flavor = host.kind;
        let steps = repair::steps_for(kind, flavor);
        let (status, sub_status) = init_status(&steps);
        Self {
            kind,
            flavor,
            steps,
            cursor: 0,
            host: Some(host.name.clone()),
            running_step: None,
            status,
            sub_status,
        }
    }

    pub fn host_attached(&self) -> bool {
        self.host.is_some()
    }

    /// Total number of cursor positions: each step = 1 (header) + N sub-checks.
    pub fn cursor_total(&self) -> usize {
        self.steps.iter().map(|s| 1 + s.checks.len()).sum()
    }

    pub fn target_at(&self, cursor: usize) -> Option<GuidesTarget> {
        let mut remaining = cursor;
        for (step_idx, step) in self.steps.iter().enumerate() {
            if remaining == 0 {
                return Some(GuidesTarget { step: step_idx, sub: None });
            }
            remaining -= 1;
            if remaining < step.checks.len() {
                return Some(GuidesTarget { step: step_idx, sub: Some(remaining) });
            }
            remaining -= step.checks.len();
        }
        None
    }

    pub fn current_target(&self) -> Option<GuidesTarget> {
        self.target_at(self.cursor)
    }

    fn set_flavor(&mut self, flavor: HostKind) {
        if flavor != self.flavor {
            self.flavor = flavor;
            self.steps = repair::steps_for(self.kind, flavor);
            let (status, sub_status) = init_status(&self.steps);
            self.status = status;
            self.sub_status = sub_status;
            self.running_step = None;
            let total = self.cursor_total();
            if self.cursor >= total {
                self.cursor = total.saturating_sub(1);
            }
        }
    }

    fn cycle_kind(&mut self, forward: bool) {
        let all = RepairKind::ALL;
        let cur = all.iter().position(|k| *k == self.kind).unwrap_or(0);
        let next = if forward {
            (cur + 1) % all.len()
        } else {
            (cur + all.len() - 1) % all.len()
        };
        if all[next] != self.kind {
            self.kind = all[next];
            self.steps = repair::steps_for(self.kind, self.flavor);
            let (status, sub_status) = init_status(&self.steps);
            self.status = status;
            self.sub_status = sub_status;
            self.running_step = None;
            self.cursor = 0;
        }
    }
}

fn init_status(steps: &[RepairStep]) -> (Vec<Option<RepairStatus>>, Vec<Vec<Option<RepairStatus>>>) {
    let status = vec![None; steps.len()];
    let sub_status = steps.iter().map(|s| vec![None; s.checks.len()]).collect();
    (status, sub_status)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PickerAction {
    /// Enter on a host opens the stepwise dashboard.
    Debug,
    /// Enter on a host opens the repair guide attached to that host.
    Guides,
}

pub struct Picker {
    pub hosts: Vec<Host>,
    pub cursor: usize,
    pub error: Option<String>,
    pub status: HashMap<String, PingStatus>,
    pub action: PickerAction,
}

pub struct Dashboard {
    pub host: String,
    pub kind: HostKind,
    pub results: BTreeMap<usize, CheckResult>,
    pub steps: StepwiseState,
    pub action: Option<ActionEvent>,
    pub debug_mode_task: Option<tokio::task::JoinHandle<()>>,
    pub repair: RepairState,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StepPhase {
    /// No sweep has started yet.
    Idle,
    /// The current step's SSH command is in flight.
    Running,
    /// The current step finished; user must press y/n/r/s to advance.
    AwaitingConfirm,
    /// All steps have been confirmed/skipped.
    Done,
}

#[derive(Debug, Clone)]
pub struct CheckPlan {
    pub category: Category,
    pub row_ids: Vec<usize>,
    /// Stable label used in the header — first row's name, plus "(+N more)"
    /// for multi-row checks like dns_resolve.
    pub label: String,
}

pub struct StepwiseState {
    pub plan: Vec<CheckPlan>,
    pub current: usize,
    pub phase: StepPhase,
}

impl StepwiseState {
    fn new() -> Self {
        Self { plan: Vec::new(), current: 0, phase: StepPhase::Idle }
    }

    pub fn total(&self) -> usize {
        self.plan.len()
    }

    pub fn current_plan(&self) -> Option<&CheckPlan> {
        self.plan.get(self.current)
    }
}

#[derive(Debug, Clone)]
pub enum RepairStatus {
    Ok(String),
    Failed(String),
}

pub struct RepairState {
    pub visible: bool,
    pub kind: RepairKind,
    pub steps: Vec<RepairStep>,
    pub cursor: usize,
    pub running_step: Option<usize>,
    pub status: Vec<Option<RepairStatus>>,
}

impl RepairState {
    fn for_host(host_kind: HostKind) -> Self {
        // Only XCP repair exists today. When more kinds land the picker UI
        // will need to choose between them; for now we initialize with XCP
        // and rebuild on demand if/when that changes.
        let kind = RepairKind::Xcp;
        let steps = repair::steps_for(kind, host_kind);
        let status = vec![None; steps.len()];
        Self {
            visible: false,
            kind,
            steps,
            cursor: 0,
            running_step: None,
            status,
        }
    }
}

impl Dashboard {
    pub fn debug_mode_on(&self) -> bool {
        self.debug_mode_task.is_some()
    }

    pub fn repair_visible(&self) -> bool {
        self.repair.visible
    }
}

impl Drop for Dashboard {
    fn drop(&mut self) {
        // Abort the held debug-mode SSH future. Combined with kill_on_drop on
        // the local ssh process, this triggers the remote bash EXIT trap that
        // removes /tmp/ree_skip_ssh_restrictions. Covers back-to-picker
        // (Stage transition drops Dashboard), normal quit (App drop unwinds
        // through Stage), and panic unwind. Process SIGKILL is also covered
        // implicitly: when our process dies, ssh's TCP closes and remote
        // sshd sends SIGHUP to the bash, firing the same trap.
        if let Some(handle) = self.debug_mode_task.take() {
            handle.abort();
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ActionKind {
    XcpBringUp,
    DebugMode,
    Repair { kind: RepairKind, step: usize },
}

#[derive(Debug, Clone)]
pub enum ActionStatus {
    Running(String),
    Ok(String),
    Failed(String),
}

#[derive(Debug, Clone)]
pub struct ActionEvent {
    pub kind: ActionKind,
    pub status: ActionStatus,
}

impl App {
    pub fn new() -> Self {
        Self { stage: Stage::Menu(Menu::new()) }
    }

    pub fn menu_up(&mut self) {
        if let Stage::Menu(m) = &mut self.stage {
            if m.cursor > 0 {
                m.cursor -= 1;
            }
        }
    }

    pub fn menu_down(&mut self) {
        if let Stage::Menu(m) = &mut self.stage {
            if m.cursor + 1 < MenuEntry::ALL.len() {
                m.cursor += 1;
            }
        }
    }

    pub fn confirm_menu(&mut self, ping_tx: UnboundedSender<PingUpdate>, set: &mut JoinSet<()>) {
        let Stage::Menu(m) = &self.stage else { return };
        match m.selected() {
            MenuEntry::Debug => {
                self.stage = Stage::Picking(Picker::load(PickerAction::Debug));
                self.dispatch_pings(ping_tx, set);
            }
            MenuEntry::Guides => {
                // Default to browse-only — no host required for reading the
                // playbook. The user attaches a host with `h` from inside
                // the guides view if they actually want to run a step.
                self.stage = Stage::Guides(GuidesView::new());
            }
        }
    }

    // Host attach/detach disabled while iterating on playbook content; the
    // bindings in main.rs are commented out. Methods kept so re-enabling is
    // a one-line change.
    #[allow(dead_code)]
    pub fn attach_host_to_guides(
        &mut self,
        ping_tx: UnboundedSender<PingUpdate>,
        set: &mut JoinSet<()>,
    ) {
        if matches!(self.stage, Stage::Guides(_)) {
            self.stage = Stage::Picking(Picker::load(PickerAction::Guides));
            self.dispatch_pings(ping_tx, set);
        }
    }

    #[allow(dead_code)]
    pub fn detach_host_from_guides(&mut self) {
        if let Stage::Guides(g) = &mut self.stage {
            if g.host.is_some() {
                let kind = g.kind;
                let flavor = g.flavor;
                let steps = repair::steps_for(kind, flavor);
                let status = vec![None; steps.len()];
                g.host = None;
                g.steps = steps;
                g.status = status;
                g.running_step = None;
                if g.cursor >= g.steps.len() {
                    g.cursor = g.steps.len().saturating_sub(1);
                }
            }
        }
    }

    pub fn back_to_menu(&mut self) {
        self.stage = Stage::Menu(Menu::new());
    }

    pub fn guides_up(&mut self) {
        if let Stage::Guides(g) = &mut self.stage {
            // In page mode, ↑/↓ stays inside the current step. Page changes
            // are explicit (← / → / PgUp / PgDn).
            let Some(target) = g.current_target() else { return };
            let page_start: usize = g
                .steps
                .iter()
                .take(target.step)
                .map(|s| 1 + s.checks.len())
                .sum();
            if g.cursor > page_start {
                g.cursor -= 1;
            }
        }
    }

    pub fn guides_down(&mut self) {
        if let Stage::Guides(g) = &mut self.stage {
            let Some(target) = g.current_target() else { return };
            let page_start: usize = g
                .steps
                .iter()
                .take(target.step)
                .map(|s| 1 + s.checks.len())
                .sum();
            let page_end_exclusive = page_start + 1 + g.steps[target.step].checks.len();
            if g.cursor + 1 < page_end_exclusive {
                g.cursor += 1;
            }
        }
    }

    pub fn guides_next_page(&mut self) {
        if let Stage::Guides(g) = &mut self.stage {
            let Some(target) = g.current_target() else { return };
            if target.step + 1 < g.steps.len() {
                let next_start: usize = g
                    .steps
                    .iter()
                    .take(target.step + 1)
                    .map(|s| 1 + s.checks.len())
                    .sum();
                g.cursor = next_start;
            }
        }
    }

    pub fn guides_next_kind(&mut self) {
        if let Stage::Guides(g) = &mut self.stage {
            g.cycle_kind(true);
        }
    }

    pub fn guides_prev_kind(&mut self) {
        if let Stage::Guides(g) = &mut self.stage {
            g.cycle_kind(false);
        }
    }

    pub fn guides_prev_page(&mut self) {
        if let Stage::Guides(g) = &mut self.stage {
            let Some(target) = g.current_target() else { return };
            if target.step > 0 {
                let prev_start: usize = g
                    .steps
                    .iter()
                    .take(target.step - 1)
                    .map(|s| 1 + s.checks.len())
                    .sum();
                g.cursor = prev_start;
            }
        }
    }

    pub fn guides_set_flavor(&mut self, flavor: HostKind) {
        if let Stage::Guides(g) = &mut self.stage {
            g.set_flavor(flavor);
        }
    }

    pub fn guides_toggle_flavor(&mut self) {
        if let Stage::Guides(g) = &mut self.stage {
            // When a host is attached, flavor is pinned by host kind —
            // toggling would let the user run TS commands against a VE host.
            if g.host.is_some() {
                return;
            }
            let next = match g.flavor {
                HostKind::Ts => HostKind::Ve,
                HostKind::Ve => HostKind::Ts,
            };
            g.set_flavor(next);
        }
    }

    pub fn run_selected_guides_step(
        &mut self,
        action_tx: UnboundedSender<ActionEvent>,
        set: &mut JoinSet<()>,
    ) {
        let Stage::Guides(g) = &mut self.stage else { return };
        let Some(target_pos) = g.current_target() else { return };

        // Browse-only walkthrough: no host means we can't actually run the
        // command, so Enter just ticks the current item (step or sub-check)
        // and advances the cursor. Useful while iterating on playbook content.
        if g.host.is_none() {
            let total = g.cursor_total();
            match target_pos.sub {
                None => {
                    // At step header: bulk-tick the step + every sub-check
                    // and skip past the sub-checks to the next step header.
                    let step_idx = target_pos.step;
                    g.status[step_idx] =
                        Some(RepairStatus::Ok("checked locally".into()));
                    for slot in &mut g.sub_status[step_idx] {
                        *slot = Some(RepairStatus::Ok("checked locally".into()));
                    }
                    let advance_by = 1 + g.steps[step_idx].checks.len();
                    g.cursor = (g.cursor + advance_by).min(total.saturating_sub(1));
                }
                Some(sub_idx) => {
                    // At a sub-check: tick this one only, advance by 1.
                    let step_idx = target_pos.step;
                    g.sub_status[step_idx][sub_idx] =
                        Some(RepairStatus::Ok("checked locally".into()));
                    // Step is implicitly done once every sub-check is.
                    if g.sub_status[step_idx].iter().all(|s| s.is_some())
                        && g.status[step_idx].is_none()
                    {
                        g.status[step_idx] =
                            Some(RepairStatus::Ok("all sub-checks done".into()));
                    }
                    if g.cursor + 1 < total {
                        g.cursor += 1;
                    }
                }
            }
            return;
        }

        // Host-attached mode: only the step header runs SSH (sub-checks are
        // manual hardware verifications without a corresponding remote
        // command). Sub-check Enter still ticks locally for now.
        let step_index = match target_pos.sub {
            None => target_pos.step,
            Some(sub_idx) => {
                let step_idx = target_pos.step;
                g.sub_status[step_idx][sub_idx] =
                    Some(RepairStatus::Ok("checked locally".into()));
                let total = g.cursor_total();
                if g.cursor + 1 < total {
                    g.cursor += 1;
                }
                return;
            }
        };
        if g.running_step.is_some() {
            return;
        }
        let Some(host_name) = g.host.clone() else { return };
        let Some(step) = g.steps.get(step_index).cloned() else { return };
        let cmd = match step.action.clone() {
            RepairAction::Inspect => return,
            RepairAction::Command(c) => c,
        };
        let kind = g.kind;
        g.running_step = Some(step_index);
        g.status[step_index] = None;
        let target = Arc::new(SshTarget::new(host_name));

        let _ = action_tx.send(ActionEvent {
            kind: ActionKind::Repair { kind, step: step_index },
            status: ActionStatus::Running(format!("{}…", step.label)),
        });

        let action_tx_task = action_tx.clone();
        set.spawn(async move {
            let status = match ree_debug_engine::ssh::run_remote(&target, &cmd).await {
                Ok(r) if r.ok() => {
                    let (rc, bus, detail) = repair::parse_rc_trailer(&r.stdout);
                    match rc {
                        Some(0) => {
                            let summary = match bus {
                                Some(b) => format!("{} ({})", step.label, b),
                                None => step.label.to_string(),
                            };
                            ActionStatus::Ok(summary)
                        }
                        Some(code) => {
                            let detail = if detail.is_empty() {
                                format!("rc={}", code)
                            } else {
                                detail
                            };
                            ActionStatus::Failed(format!("{}: {}", step.label, detail))
                        }
                        None => ActionStatus::Failed(format!(
                            "{}: unexpected output: {}",
                            step.label,
                            r.stdout.trim()
                        )),
                    }
                }
                Ok(r) => ActionStatus::Failed(format!(
                    "{}: ssh exit {:?}: {}",
                    step.label,
                    r.exit_code,
                    r.stderr.trim()
                )),
                Err(e) => ActionStatus::Failed(format!("{}: ssh error: {}", step.label, e)),
            };
            let _ = action_tx_task.send(ActionEvent {
                kind: ActionKind::Repair { kind, step: step_index },
                status,
            });
        });
    }

    pub fn picker_up(&mut self) {
        if let Stage::Picking(p) = &mut self.stage {
            if p.cursor > 0 {
                p.cursor -= 1;
            }
        }
    }

    pub fn picker_down(&mut self) {
        if let Stage::Picking(p) = &mut self.stage {
            if p.cursor + 1 < p.hosts.len() {
                p.cursor += 1;
            }
        }
    }

    pub fn confirm_pick(&mut self, tx: UnboundedSender<CheckResult>, set: &mut JoinSet<()>) {
        let (chosen, action) = if let Stage::Picking(p) = &self.stage {
            (p.hosts.get(p.cursor).cloned(), p.action)
        } else {
            (None, PickerAction::Debug)
        };
        let Some(h) = chosen else { return };
        match action {
            PickerAction::Debug => {
                let repair = RepairState::for_host(h.kind);
                let mut dash = Dashboard {
                    host: h.name,
                    kind: h.kind,
                    results: BTreeMap::new(),
                    steps: StepwiseState::new(),
                    action: None,
                    debug_mode_task: None,
                    repair,
                };
                dash.start_sweep(tx, set);
                self.stage = Stage::Dashboard(dash);
            }
            PickerAction::Guides => {
                self.stage = Stage::Guides(GuidesView::for_host(&h));
            }
        }
    }

    pub fn rerun(&mut self, tx: UnboundedSender<CheckResult>, set: &mut JoinSet<()>) {
        if let Stage::Dashboard(d) = &mut self.stage {
            d.start_sweep(tx, set);
        }
    }

    pub fn confirm_current_step(
        &mut self,
        tx: UnboundedSender<CheckResult>,
        set: &mut JoinSet<()>,
    ) {
        if let Stage::Dashboard(d) = &mut self.stage {
            d.confirm_current_step(tx, set);
        }
    }

    pub fn override_current_step(
        &mut self,
        tx: UnboundedSender<CheckResult>,
        set: &mut JoinSet<()>,
    ) {
        if let Stage::Dashboard(d) = &mut self.stage {
            d.override_current_step(tx, set);
        }
    }

    pub fn rerun_current_step(
        &mut self,
        tx: UnboundedSender<CheckResult>,
        set: &mut JoinSet<()>,
    ) {
        if let Stage::Dashboard(d) = &mut self.stage {
            d.dispatch_current_step(tx, set);
        }
    }

    pub fn skip_current_step(
        &mut self,
        tx: UnboundedSender<CheckResult>,
        set: &mut JoinSet<()>,
    ) {
        if let Stage::Dashboard(d) = &mut self.stage {
            d.skip_current_step(tx, set);
        }
    }

    pub fn dispatch_bring_up_xcp(
        &mut self,
        action_tx: UnboundedSender<ActionEvent>,
        set: &mut JoinSet<()>,
    ) {
        if let Stage::Dashboard(d) = &mut self.stage {
            d.dispatch_bring_up_xcp(action_tx, set);
        }
    }

    pub fn toggle_debug_mode(&mut self, action_tx: UnboundedSender<ActionEvent>) {
        if let Stage::Dashboard(d) = &mut self.stage {
            d.toggle_debug_mode(action_tx);
        }
    }

    pub fn repair_open(&self) -> bool {
        matches!(&self.stage, Stage::Dashboard(d) if d.repair_visible())
    }

    pub fn toggle_repair_guide(&mut self) {
        if let Stage::Dashboard(d) = &mut self.stage {
            d.repair.visible = !d.repair.visible;
        }
    }

    pub fn close_repair_guide(&mut self) {
        if let Stage::Dashboard(d) = &mut self.stage {
            d.repair.visible = false;
        }
    }

    pub fn repair_cursor_up(&mut self) {
        if let Stage::Dashboard(d) = &mut self.stage {
            if d.repair.cursor > 0 {
                d.repair.cursor -= 1;
            }
        }
    }

    pub fn repair_cursor_down(&mut self) {
        if let Stage::Dashboard(d) = &mut self.stage {
            if d.repair.cursor + 1 < d.repair.steps.len() {
                d.repair.cursor += 1;
            }
        }
    }

    pub fn run_selected_repair_step(
        &mut self,
        action_tx: UnboundedSender<ActionEvent>,
        set: &mut JoinSet<()>,
    ) {
        if let Stage::Dashboard(d) = &mut self.stage {
            d.run_selected_repair_step(action_tx, set);
        }
    }

    pub fn ingest_action(&mut self, event: ActionEvent) {
        // Route Repair events to the standalone guides view too — same
        // payload, the view tracks per-step status the same way the
        // dashboard's repair overlay does.
        if let Stage::Guides(g) = &mut self.stage {
            if let ActionKind::Repair { step, .. } = event.kind {
                if step < g.status.len() {
                    match &event.status {
                        ActionStatus::Running(_) => {
                            g.running_step = Some(step);
                            g.status[step] = None;
                        }
                        ActionStatus::Ok(t) => {
                            g.running_step = None;
                            g.status[step] = Some(RepairStatus::Ok(t.clone()));
                        }
                        ActionStatus::Failed(t) => {
                            g.running_step = None;
                            g.status[step] = Some(RepairStatus::Failed(t.clone()));
                        }
                    }
                }
            }
            return;
        }
        if let Stage::Dashboard(d) = &mut self.stage {
            // If the debug-mode task reported a failure, the spawned future
            // has already exited — drop the handle so debug_mode_on()
            // reflects reality and a subsequent `d` press starts fresh
            // instead of trying to abort a dead handle.
            if matches!(
                &event,
                ActionEvent { kind: ActionKind::DebugMode, status: ActionStatus::Failed(_) }
            ) {
                d.debug_mode_task = None;
            }
            // Repair events also feed the overlay's per-step status so the
            // user sees ✓/✗ next to the step they ran. The header status
            // line still updates so the result is visible if the overlay
            // is closed before the step completes.
            if let ActionKind::Repair { step, .. } = event.kind {
                if step < d.repair.status.len() {
                    match &event.status {
                        ActionStatus::Running(_) => {
                            d.repair.running_step = Some(step);
                            d.repair.status[step] = None;
                        }
                        ActionStatus::Ok(t) => {
                            d.repair.running_step = None;
                            d.repair.status[step] = Some(RepairStatus::Ok(t.clone()));
                        }
                        ActionStatus::Failed(t) => {
                            d.repair.running_step = None;
                            d.repair.status[step] = Some(RepairStatus::Failed(t.clone()));
                        }
                    }
                }
            }
            d.action = Some(event);
        }
    }

    pub fn back_to_picker(&mut self, ping_tx: UnboundedSender<PingUpdate>, set: &mut JoinSet<()>) {
        // Esc from the dashboard always returns to the Debug picker (that's
        // where we came from). Guides has its own back-to-menu path.
        self.stage = Stage::Picking(Picker::load(PickerAction::Debug));
        self.dispatch_pings(ping_tx, set);
    }

    pub fn dispatch_pings(&mut self, tx: UnboundedSender<PingUpdate>, set: &mut JoinSet<()>) {
        let Stage::Picking(picker) = &mut self.stage else { return };
        for h in &picker.hosts {
            picker.status.insert(h.name.clone(), PingStatus::Probing);
            let name = h.name.clone();
            let target = h.ansible_host.clone().unwrap_or_else(|| h.name.clone());
            let tx = tx.clone();
            set.spawn(async move {
                let online = ping::probe_ssh(&target, 1500).await;
                let _ = tx.send(PingUpdate {
                    host: name,
                    status: if online { PingStatus::Online } else { PingStatus::Offline },
                });
            });
        }
    }

    pub fn ingest_ping(&mut self, update: PingUpdate) {
        if let Stage::Picking(p) = &mut self.stage {
            p.status.insert(update.host, update.status);
        }
    }

    pub fn ingest(&mut self, result: CheckResult) {
        if let Stage::Dashboard(d) = &mut self.stage {
            d.results.insert(result.id, result);
            if d.steps.phase == StepPhase::Running {
                if let Some(plan) = d.steps.plan.get(d.steps.current) {
                    let all_done = plan.row_ids.iter().all(|id| {
                        d.results
                            .get(id)
                            .is_some_and(|r| r.outcome != Outcome::Pending)
                    });
                    if all_done {
                        d.steps.phase = StepPhase::AwaitingConfirm;
                    }
                }
            }
        }
    }
}

impl Picker {
    fn load(action: PickerAction) -> Self {
        match load_default() {
            Ok(mut hosts) => {
                // Scope to DE hosts only for now — keeps probes fast and the list
                // tight while we iterate. Easy to drop the filter later.
                hosts.retain(|h| h.name.contains("-de-"));
                let status = hosts
                    .iter()
                    .map(|h| (h.name.clone(), PingStatus::Unknown))
                    .collect();
                Picker { hosts, cursor: 0, error: None, status, action }
            }
            Err(e) => Picker {
                hosts: Vec::new(),
                cursor: 0,
                error: Some(e.to_string()),
                status: HashMap::new(),
                action,
            },
        }
    }

    pub fn ping_counts(&self) -> (usize, usize, usize, usize) {
        let mut online = 0;
        let mut offline = 0;
        let mut probing = 0;
        let mut unknown = 0;
        for status in self.status.values() {
            match status {
                PingStatus::Online => online += 1,
                PingStatus::Offline => offline += 1,
                PingStatus::Probing => probing += 1,
                PingStatus::Unknown => unknown += 1,
            }
        }
        (online, offline, probing, unknown)
    }
}

impl Dashboard {
    fn dispatch_bring_up_xcp(
        &mut self,
        action_tx: UnboundedSender<ActionEvent>,
        set: &mut JoinSet<()>,
    ) {
        // Already in flight — ignore re-presses so we don't pile up sudo runs.
        if matches!(
            self.action,
            Some(ActionEvent { kind: ActionKind::XcpBringUp, status: ActionStatus::Running(_) })
        ) {
            return;
        }
        let target = Arc::new(SshTarget::new(self.host.clone()));
        let default_bus = match self.kind {
            HostKind::Ts => "can2",
            HostKind::Ve => "can1",
        };
        self.action = Some(ActionEvent {
            kind: ActionKind::XcpBringUp,
            status: ActionStatus::Running(format!("bringing up {}…", default_bus)),
        });
        set.spawn(async move {
            let cmd = format!(
                "BUS=$(grep ^CAN_BUS_XCP= /etc/ree/can_bus_map 2>/dev/null | cut -d= -f2); \
                 [ -n \"$BUS\" ] || BUS={default_bus}; \
                 sudo -n ip link set \"$BUS\" up type can \
                   bitrate 500000 sample-point 0.75 \
                   dbitrate 2500000 dsample-point 0.75 \
                   restart-ms 10 fd on 2>&1; \
                 RC=$?; echo \"BUS=$BUS\"; echo \"RC=$RC\""
            );
            let status = match ree_debug_engine::ssh::run_remote(&target, &cmd).await {
                Ok(r) if r.ok() => {
                    let bus = r
                        .stdout
                        .lines()
                        .find_map(|l| l.strip_prefix("BUS="))
                        .map(|s| s.trim().to_string())
                        .unwrap_or_else(|| default_bus.to_string());
                    let rc = r
                        .stdout
                        .lines()
                        .find_map(|l| l.strip_prefix("RC="))
                        .and_then(|s| s.trim().parse::<i32>().ok())
                        .unwrap_or(-1);
                    if rc == 0 {
                        ActionStatus::Ok(format!("{} brought up", bus))
                    } else {
                        let detail = r
                            .stdout
                            .lines()
                            .filter(|l| !l.starts_with("BUS=") && !l.starts_with("RC="))
                            .collect::<Vec<_>>()
                            .join(" ");
                        let detail = if detail.trim().is_empty() {
                            format!("rc={}", rc)
                        } else {
                            detail.trim().to_string()
                        };
                        ActionStatus::Failed(format!("{}: {}", bus, detail))
                    }
                }
                Ok(r) => ActionStatus::Failed(format!(
                    "ssh exit {:?}: {}",
                    r.exit_code,
                    r.stderr.trim()
                )),
                Err(e) => ActionStatus::Failed(format!("ssh error: {}", e)),
            };
            let _ = action_tx.send(ActionEvent { kind: ActionKind::XcpBringUp, status });
        });
    }

    fn run_selected_repair_step(
        &mut self,
        action_tx: UnboundedSender<ActionEvent>,
        set: &mut JoinSet<()>,
    ) {
        // Don't queue another step while one is in flight — sudo prompts
        // would race and the bus could get torn down mid-bring-up.
        if self.repair.running_step.is_some() {
            return;
        }
        let step_index = self.repair.cursor;
        let Some(step) = self.repair.steps.get(step_index).cloned() else {
            return;
        };
        // Hardware checklists are read-only; nothing to dispatch over SSH.
        // The user verifies them on the bench, not via Enter.
        let cmd = match step.action.clone() {
            RepairAction::Inspect => return,
            RepairAction::Command(c) => c,
        };
        let kind = self.repair.kind;
        self.repair.running_step = Some(step_index);
        self.repair.status[step_index] = None;
        let target = Arc::new(SshTarget::new(self.host.clone()));

        // Optimistic Running event so the header + overlay show progress.
        let _ = action_tx.send(ActionEvent {
            kind: ActionKind::Repair { kind, step: step_index },
            status: ActionStatus::Running(format!("{}…", step.label)),
        });

        let action_tx_task = action_tx.clone();
        set.spawn(async move {
            let status = match ree_debug_engine::ssh::run_remote(&target, &cmd).await {
                Ok(r) if r.ok() => {
                    let (rc, bus, detail) = repair::parse_rc_trailer(&r.stdout);
                    match rc {
                        Some(0) => {
                            let summary = match bus {
                                Some(b) => format!("{} ({})", step.label, b),
                                None => step.label.to_string(),
                            };
                            ActionStatus::Ok(summary)
                        }
                        Some(code) => {
                            let detail = if detail.is_empty() {
                                format!("rc={}", code)
                            } else {
                                detail
                            };
                            ActionStatus::Failed(format!("{}: {}", step.label, detail))
                        }
                        None => {
                            // No RC trailer — treat unparseable output as
                            // failure rather than silently claiming success.
                            ActionStatus::Failed(format!(
                                "{}: unexpected output: {}",
                                step.label,
                                r.stdout.trim()
                            ))
                        }
                    }
                }
                Ok(r) => ActionStatus::Failed(format!(
                    "{}: ssh exit {:?}: {}",
                    step.label,
                    r.exit_code,
                    r.stderr.trim()
                )),
                Err(e) => ActionStatus::Failed(format!("{}: ssh error: {}", step.label, e)),
            };
            let _ = action_tx_task.send(ActionEvent {
                kind: ActionKind::Repair { kind, step: step_index },
                status,
            });
        });
    }

    fn toggle_debug_mode(&mut self, action_tx: UnboundedSender<ActionEvent>) {
        // Currently ON → abort the held SSH future. kill_on_drop fires SIGKILL
        // to the local ssh client, the remote sshd sends SIGHUP to the bash
        // session, and bash's EXIT trap removes the sentinel file.
        if let Some(handle) = self.debug_mode_task.take() {
            handle.abort();
            self.action = Some(ActionEvent {
                kind: ActionKind::DebugMode,
                status: ActionStatus::Ok("debug mode off".into()),
            });
            return;
        }

        // Currently OFF → spawn a long-lived ssh that touches the sentinel
        // and parks forever. Cleanup is owned by the remote EXIT trap; we
        // only need to abort the local future to trigger it.
        let target = Arc::new(SshTarget::new(self.host.clone()));
        // Only trap EXIT — NOT TERM/HUP/INT. Trapping signals without
        // calling `exit` from the trap (as we used to) means the trap runs
        // the rm and then bash *resumes* the sleep loop instead of dying.
        // Net effect: SIGTERM/SIGHUP have no effect. Letting the default
        // signal action run (terminate) means EXIT trap fires automatically
        // on signal-induced exit and the file is removed.
        let cmd = "trap 'rm -f /tmp/ree_skip_ssh_restrictions' EXIT; \
                   touch /tmp/ree_skip_ssh_restrictions || exit 1; \
                   while :; do sleep 3600; done";
        let action_tx_task = action_tx.clone();
        let handle = tokio::spawn(async move {
            // Surface only failures and unexpected exits back to the UI; the
            // happy path returns by abort, in which case this future is
            // dropped and the match arms never run.
            match ree_debug_engine::ssh::run_remote(&target, cmd).await {
                Ok(r) if r.ok() => {
                    let _ = action_tx_task.send(ActionEvent {
                        kind: ActionKind::DebugMode,
                        status: ActionStatus::Failed("debug-mode session ended unexpectedly".into()),
                    });
                }
                Ok(r) => {
                    let detail = if !r.stderr.trim().is_empty() {
                        r.stderr.trim().to_string()
                    } else {
                        format!("exit {:?}", r.exit_code)
                    };
                    let _ = action_tx_task.send(ActionEvent {
                        kind: ActionKind::DebugMode,
                        status: ActionStatus::Failed(detail),
                    });
                }
                Err(e) => {
                    let _ = action_tx_task.send(ActionEvent {
                        kind: ActionKind::DebugMode,
                        status: ActionStatus::Failed(format!("ssh error: {}", e)),
                    });
                }
            }
        });
        self.debug_mode_task = Some(handle);
        // Optimistic — if the SSH connect or `touch` fails, the task above
        // will overwrite this with Failed within a few hundred ms.
        let _ = action_tx.send(ActionEvent {
            kind: ActionKind::DebugMode,
            status: ActionStatus::Ok("debug mode on".into()),
        });
    }

    /// Build the stepwise plan, seed `results` with queued rows, and dispatch
    /// the first step. Called on dashboard entry and on re-runs (e.g. after a
    /// successful XCP bring-up).
    fn start_sweep(&mut self, tx: UnboundedSender<CheckResult>, set: &mut JoinSet<()>) {
        let checks = all_checks(self.kind);
        self.results.clear();
        let mut plan: Vec<CheckPlan> = Vec::with_capacity(checks.len());
        for check in &checks {
            let row_ids: Vec<usize> = check.planned.iter().map(|r| r.id).collect();
            for row in &check.planned {
                self.results.insert(
                    row.id,
                    CheckResult {
                        id: row.id,
                        category: check.category,
                        name: row.name.into(),
                        outcome: Outcome::Pending,
                        summary: "queued…".into(),
                        raw: String::new(),
                    },
                );
            }
            let first_name = check.planned.first().map(|r| r.name).unwrap_or("?");
            let label = if check.planned.len() > 1 {
                format!("{} (+{} more)", first_name, check.planned.len() - 1)
            } else {
                first_name.to_string()
            };
            plan.push(CheckPlan {
                category: check.category,
                row_ids,
                label,
            });
        }
        self.steps = StepwiseState {
            plan,
            current: 0,
            phase: StepPhase::Idle,
        };
        self.dispatch_current_step(tx, set);
    }

    /// Dispatch (or re-dispatch) the current step. Used both for normal
    /// advancement and for the `r` re-run key while AwaitingConfirm.
    fn dispatch_current_step(
        &mut self,
        tx: UnboundedSender<CheckResult>,
        set: &mut JoinSet<()>,
    ) {
        let index = self.steps.current;
        let Some(plan) = self.steps.plan.get(index).cloned() else {
            self.steps.phase = StepPhase::Done;
            return;
        };
        // Mark the rows for this step as Pending again so a re-run doesn't
        // leave the previous outcome lingering during the SSH round-trip.
        for id in &plan.row_ids {
            if let Some(r) = self.results.get_mut(id) {
                r.outcome = Outcome::Pending;
                r.summary = "running…".into();
                r.raw.clear();
            }
        }
        self.steps.phase = StepPhase::Running;
        let Some(check) = all_checks(self.kind).into_iter().nth(index) else {
            self.steps.phase = StepPhase::Done;
            return;
        };
        let target = Arc::new(SshTarget::new(self.host.clone()));
        let category = check.category;
        let planned = check.planned;
        let run = check.run;
        let tx = tx.clone();
        set.spawn(async move {
            let results = run(target, category, planned).await;
            for r in results {
                let _ = tx.send(r);
            }
        });
    }

    fn advance_step(&mut self, tx: UnboundedSender<CheckResult>, set: &mut JoinSet<()>) {
        self.steps.current += 1;
        if self.steps.current >= self.steps.plan.len() {
            self.steps.phase = StepPhase::Done;
        } else {
            self.dispatch_current_step(tx, set);
        }
    }

    fn confirm_current_step(
        &mut self,
        tx: UnboundedSender<CheckResult>,
        set: &mut JoinSet<()>,
    ) {
        if self.steps.phase != StepPhase::AwaitingConfirm {
            return;
        }
        self.advance_step(tx, set);
    }

    fn override_current_step(
        &mut self,
        tx: UnboundedSender<CheckResult>,
        set: &mut JoinSet<()>,
    ) {
        if self.steps.phase != StepPhase::AwaitingConfirm {
            return;
        }
        let row_ids = match self.steps.plan.get(self.steps.current) {
            Some(p) => p.row_ids.clone(),
            None => return,
        };
        for id in &row_ids {
            if let Some(r) = self.results.get_mut(id) {
                // Pending shouldn't reach AwaitingConfirm; treat as no-op.
                r.outcome = match r.outcome {
                    Outcome::Ok => Outcome::Fail,
                    Outcome::Warn => Outcome::Fail,
                    Outcome::Fail => Outcome::Ok,
                    Outcome::Pending => Outcome::Pending,
                };
                if !r.summary.starts_with("(overridden)") {
                    r.summary = format!("(overridden) {}", r.summary);
                }
            }
        }
        self.advance_step(tx, set);
    }

    fn skip_current_step(
        &mut self,
        tx: UnboundedSender<CheckResult>,
        set: &mut JoinSet<()>,
    ) {
        if self.steps.phase != StepPhase::AwaitingConfirm {
            return;
        }
        let row_ids = match self.steps.plan.get(self.steps.current) {
            Some(p) => p.row_ids.clone(),
            None => return,
        };
        for id in &row_ids {
            if let Some(r) = self.results.get_mut(id) {
                r.outcome = Outcome::Warn;
                r.summary = "skipped by user".into();
            }
        }
        self.advance_step(tx, set);
    }
}
