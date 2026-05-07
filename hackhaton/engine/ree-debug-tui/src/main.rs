// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

mod app;
mod repair;
mod ui;

use std::io;
use std::time::Duration;

use anyhow::Result;
use crossterm::{
    event::{self, Event, KeyCode, KeyEventKind},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, Terminal};
use tokio::sync::mpsc;
use tokio::task::JoinSet;

use crate::app::{ActionEvent, ActionKind, ActionStatus, App, Stage};
use ree_debug_engine::inventory::HostKind;

#[tokio::main]
async fn main() -> Result<()> {
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let result = run(&mut terminal).await;

    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    terminal.show_cursor()?;

    result
}

async fn run<B: ratatui::backend::Backend>(terminal: &mut Terminal<B>) -> Result<()> {
    let mut app = App::new();
    let (tx, mut rx) = mpsc::unbounded_channel();
    let (ping_tx, mut ping_rx) = mpsc::unbounded_channel();
    let (action_tx, mut action_rx) = mpsc::unbounded_channel::<ActionEvent>();
    let mut set: JoinSet<()> = JoinSet::new();
    let mut tick: u64 = 0;

    // Pings start when the user enters the picker from the menu — see
    // `confirm_menu`. The app boots into the menu, so there's nothing to
    // probe yet.

    loop {
        terminal.draw(|f| ui::draw(f, &app, tick))?;
        tick = tick.wrapping_add(1);

        while let Ok(result) = rx.try_recv() {
            app.ingest(result);
        }
        while let Ok(update) = ping_rx.try_recv() {
            app.ingest_ping(update);
        }
        let mut rerun_checks = false;
        while let Ok(e) = action_rx.try_recv() {
            // XCP bring-up and successful repair steps invalidate the
            // current check results, so re-run everything. Debug-mode
            // toggles are persistent state, not transient conditions.
            if matches!(&e.status, ActionStatus::Ok(_))
                && matches!(
                    &e.kind,
                    ActionKind::XcpBringUp | ActionKind::Repair { .. }
                )
            {
                rerun_checks = true;
            }
            app.ingest_action(e);
        }
        if rerun_checks {
            set.shutdown().await;
            while rx.try_recv().is_ok() {}
            app.rerun(tx.clone(), &mut set);
        }

        if !event::poll(Duration::from_millis(100))? {
            continue;
        }
        let Event::Key(key) = event::read()? else { continue };
        if key.kind != KeyEventKind::Press {
            continue;
        }

        if matches!(app.stage, Stage::Menu(_)) {
            match key.code {
                KeyCode::Char('q') | KeyCode::Esc => return Ok(()),
                KeyCode::Up | KeyCode::Char('k') => app.menu_up(),
                KeyCode::Down | KeyCode::Char('j') => app.menu_down(),
                KeyCode::Enter => app.confirm_menu(ping_tx.clone(), &mut set),
                _ => {}
            }
        } else if matches!(app.stage, Stage::Guides(_)) {
            match key.code {
                KeyCode::Char('q') => return Ok(()),
                KeyCode::Esc => app.back_to_menu(),
                KeyCode::Up | KeyCode::Char('k') => app.guides_up(),
                KeyCode::Down | KeyCode::Char('j') => app.guides_down(),
                // Page-flip — workshop-manual style. ←/→, PgUp/PgDn, n/p.
                KeyCode::Right
                | KeyCode::PageDown
                | KeyCode::Char('l')
                | KeyCode::Char('n') => app.guides_next_page(),
                KeyCode::Left
                | KeyCode::PageUp
                | KeyCode::Char('p') => app.guides_prev_page(),
                // Cycle between repair kinds (e.g. XCP ↔ SW Buttons).
                KeyCode::Char(']') => app.guides_next_kind(),
                KeyCode::Char('[') => app.guides_prev_kind(),
                KeyCode::Enter => {
                    app.run_selected_guides_step(action_tx.clone(), &mut set);
                }
                // Host attach/detach disabled while we iterate on playbook
                // content — re-enable when the run-on-host flow is wanted.
                // KeyCode::Char('h') => {
                //     app.attach_host_to_guides(ping_tx.clone(), &mut set);
                // }
                // KeyCode::Char('H') => app.detach_host_from_guides(),
                // Flavor toggle only applies in browse-only mode (host is
                // None). With a host attached the flavor is pinned, so these
                // keys become inert.
                KeyCode::Tab => app.guides_toggle_flavor(),
                KeyCode::Char('t') | KeyCode::Char('T') => {
                    app.guides_set_flavor(HostKind::Ts);
                }
                KeyCode::Char('v') | KeyCode::Char('V') => {
                    app.guides_set_flavor(HostKind::Ve);
                }
                _ => {}
            }
        } else if matches!(app.stage, Stage::Picking(_)) {
            match key.code {
                KeyCode::Char('q') => return Ok(()),
                KeyCode::Esc => {
                    while ping_rx.try_recv().is_ok() {}
                    set.shutdown().await;
                    app.back_to_menu();
                }
                KeyCode::Up | KeyCode::Char('k') => app.picker_up(),
                KeyCode::Down | KeyCode::Char('j') => app.picker_down(),
                KeyCode::Enter => app.confirm_pick(tx.clone(), &mut set),
                _ => {}
            }
        } else if app.repair_open() {
            // Overlay-modal keys: navigate steps and run the selected one.
            // Esc closes the overlay without leaving the dashboard so the
            // user can inspect re-run results behind it.
            match key.code {
                KeyCode::Esc | KeyCode::Char('f') | KeyCode::Char('q') => {
                    app.close_repair_guide();
                }
                KeyCode::Up | KeyCode::Char('k') => app.repair_cursor_up(),
                KeyCode::Down | KeyCode::Char('j') => app.repair_cursor_down(),
                KeyCode::Enter => {
                    app.run_selected_repair_step(action_tx.clone(), &mut set);
                }
                _ => {}
            }
        } else {
            // Stepwise dashboard keys.
            // y/Enter: accept current step and advance.
            // n: override (flip Ok↔Fail, Warn→Fail) and advance.
            // r: re-run current step.
            // s: skip current step (mark Warn "skipped by user") and advance.
            // R (Shift+R): restart the whole sweep from step 0.
            match key.code {
                KeyCode::Char('q') => return Ok(()),
                KeyCode::Esc => {
                    set.shutdown().await;
                    while rx.try_recv().is_ok() {}
                    while ping_rx.try_recv().is_ok() {}
                    app.back_to_picker(ping_tx.clone(), &mut set);
                }
                KeyCode::Char('y') | KeyCode::Enter => {
                    app.confirm_current_step(tx.clone(), &mut set);
                }
                KeyCode::Char('n') => {
                    app.override_current_step(tx.clone(), &mut set);
                }
                KeyCode::Char('r') => {
                    app.rerun_current_step(tx.clone(), &mut set);
                }
                KeyCode::Char('s') => {
                    app.skip_current_step(tx.clone(), &mut set);
                }
                KeyCode::Char('R') => {
                    set.shutdown().await;
                    while rx.try_recv().is_ok() {}
                    app.rerun(tx.clone(), &mut set);
                }
                KeyCode::Char('b') => {
                    app.dispatch_bring_up_xcp(action_tx.clone(), &mut set);
                }
                KeyCode::Char('d') => {
                    app.toggle_debug_mode(action_tx.clone());
                }
                KeyCode::Char('f') => {
                    app.toggle_repair_guide();
                }
                _ => {}
            }
        }
    }
}
