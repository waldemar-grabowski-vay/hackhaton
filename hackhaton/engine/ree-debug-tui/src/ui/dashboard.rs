// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, Paragraph, Wrap},
    Frame,
};

use crate::app::{ActionStatus, Dashboard, RepairStatus, StepPhase};
use ree_debug_engine::checks::{Category, CheckResult, Outcome};
use ree_debug_engine::inventory::HostKind;
use crate::repair::RepairAction;
use crate::ui::{keyhint, spinner_frame};

const DEBUG_TAG_BG: Color = Color::Red;

const NAME_WIDTH: usize = 32;

pub fn draw(f: &mut Frame, dash: &Dashboard, tick: u64) {
    let area = f.area();
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),
            Constraint::Length(1),
            Constraint::Min(0),
            Constraint::Length(1),
        ])
        .split(area);

    draw_header(f, chunks[0], dash, tick);
    draw_step_bar(f, chunks[1], dash, tick);
    draw_body(f, chunks[2], dash, tick);
    draw_footer(f, chunks[3], dash);

    if dash.repair.visible {
        draw_repair_overlay(f, dash, tick);
    }
}

fn draw_header(f: &mut Frame, area: Rect, dash: &Dashboard, tick: u64) {
    let kind_color = match dash.kind {
        HostKind::Ts => Color::Cyan,
        HostKind::Ve => Color::Magenta,
    };
    let kind_badge = Span::styled(
        format!(" {} ", dash.kind.tag()),
        Style::default()
            .bg(kind_color)
            .fg(Color::Black)
            .add_modifier(Modifier::BOLD),
    );
    let host = Span::styled(
        format!("  {}", dash.host),
        Style::default().add_modifier(Modifier::BOLD),
    );

    let counts = count_results(dash.results.values());
    let mut spans = vec![kind_badge, host];
    if dash.debug_mode_on() {
        spans.push(Span::raw("  "));
        spans.push(Span::styled(
            " DEBUG ",
            Style::default()
                .bg(DEBUG_TAG_BG)
                .fg(Color::Black)
                .add_modifier(Modifier::BOLD),
        ));
    }
    spans.push(Span::raw("    "));
    spans.extend([
        Span::styled(
            format!("✓ {}", counts.ok),
            Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
        ),
        Span::raw("  "),
        Span::styled(
            format!("⚠ {}", counts.warn),
            Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
        ),
        Span::raw("  "),
        Span::styled(
            format!("✗ {}", counts.fail),
            Style::default().fg(Color::Red).add_modifier(Modifier::BOLD),
        ),
        Span::raw("    "),
    ]);

    match dash.steps.phase {
        StepPhase::Idle | StepPhase::Running | StepPhase::AwaitingConfirm => {
            spans.push(Span::styled(
                format!("step {} / {}", dash.steps.current + 1, dash.steps.total().max(1)),
                Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
            ));
        }
        StepPhase::Done => {
            if counts.fail > 0 {
                spans.push(Span::styled(
                    "sweep complete — issues found",
                    Style::default().fg(Color::Red).add_modifier(Modifier::BOLD),
                ));
            } else if counts.warn > 0 {
                spans.push(Span::styled(
                    "sweep complete — warnings",
                    Style::default().fg(Color::Yellow),
                ));
            } else {
                spans.push(Span::styled(
                    "sweep complete — all green",
                    Style::default().fg(Color::Green),
                ));
            }
        }
    }

    if let Some(event) = &dash.action {
        spans.push(Span::raw("    "));
        let (icon, color, text) = match &event.status {
            ActionStatus::Running(t) => (spinner_frame(tick).to_string(), Color::Cyan, t.as_str()),
            ActionStatus::Ok(t) => ("✓".into(), Color::Green, t.as_str()),
            ActionStatus::Failed(t) => ("✗".into(), Color::Red, t.as_str()),
        };
        spans.push(Span::styled(
            format!("{} {}", icon, text),
            Style::default().fg(color).add_modifier(Modifier::BOLD),
        ));
    }

    let block = Block::default()
        .borders(Borders::ALL)
        .title(Span::styled(
            " ree-debug-tui ",
            Style::default().add_modifier(Modifier::BOLD),
        ))
        .border_style(Style::default().fg(Color::DarkGray));
    f.render_widget(Paragraph::new(Line::from(spans)).block(block), area);
}

fn draw_step_bar(f: &mut Frame, area: Rect, dash: &Dashboard, tick: u64) {
    let mut spans: Vec<Span> = Vec::new();
    let label = dash
        .steps
        .current_plan()
        .map(|p| p.label.as_str())
        .unwrap_or("");
    let category_label = dash
        .steps
        .current_plan()
        .map(|p| p.category.label())
        .unwrap_or("");

    match dash.steps.phase {
        StepPhase::Idle => {
            spans.push(Span::styled(
                "  preparing sweep…",
                Style::default().fg(Color::DarkGray),
            ));
        }
        StepPhase::Running => {
            spans.push(Span::raw("  "));
            spans.push(Span::styled(
                spinner_frame(tick).to_string(),
                Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
            ));
            spans.push(Span::raw("  "));
            spans.push(Span::styled(
                format!("[{}] ", category_label),
                Style::default().fg(Color::Cyan),
            ));
            spans.push(Span::styled(
                label.to_string(),
                Style::default().add_modifier(Modifier::BOLD),
            ));
            spans.push(Span::styled(
                "  — running…",
                Style::default().fg(Color::DarkGray),
            ));
        }
        StepPhase::AwaitingConfirm => {
            // Outcome of the current step's rows — worst outcome wins so the
            // user sees ✗ if any sub-row failed.
            let outcome = dash
                .steps
                .current_plan()
                .map(|p| {
                    p.row_ids
                        .iter()
                        .filter_map(|id| dash.results.get(id))
                        .map(|r| r.outcome)
                        .fold(Outcome::Ok, worst_outcome)
                })
                .unwrap_or(Outcome::Pending);
            let (icon, color) = match outcome {
                Outcome::Ok => ("✓", Color::Green),
                Outcome::Warn => ("⚠", Color::Yellow),
                Outcome::Fail => ("✗", Color::Red),
                Outcome::Pending => ("·", Color::DarkGray),
            };
            spans.push(Span::raw("  "));
            spans.push(Span::styled(
                icon.to_string(),
                Style::default().fg(color).add_modifier(Modifier::BOLD),
            ));
            spans.push(Span::raw("  "));
            spans.push(Span::styled(
                format!("[{}] ", category_label),
                Style::default().fg(Color::Cyan),
            ));
            spans.push(Span::styled(
                label.to_string(),
                Style::default().add_modifier(Modifier::BOLD),
            ));
            spans.push(Span::styled(
                "  — confirm? ",
                Style::default().fg(Color::DarkGray),
            ));
            spans.push(keyhint("y/Enter"));
            spans.push(Span::raw(" pass  "));
            spans.push(keyhint("n"));
            spans.push(Span::raw(" override  "));
            spans.push(keyhint("r"));
            spans.push(Span::raw(" rerun  "));
            spans.push(keyhint("s"));
            spans.push(Span::raw(" skip"));
        }
        StepPhase::Done => {
            spans.push(Span::styled(
                "  sweep complete — ",
                Style::default().fg(Color::DarkGray),
            ));
            spans.push(keyhint("R"));
            spans.push(Span::raw(" restart   "));
            spans.push(keyhint("f"));
            spans.push(Span::raw(" repair guide"));
        }
    }
    f.render_widget(Paragraph::new(Line::from(spans)), area);
}

fn worst_outcome(a: Outcome, b: Outcome) -> Outcome {
    use Outcome::*;
    match (a, b) {
        (Fail, _) | (_, Fail) => Fail,
        (Pending, _) | (_, Pending) => Pending,
        (Warn, _) | (_, Warn) => Warn,
        _ => Ok,
    }
}

fn draw_body(f: &mut Frame, area: Rect, dash: &Dashboard, tick: u64) {
    let mut lines: Vec<Line> = Vec::new();
    let categories = [
        Category::Connectivity,
        Category::Reecu,
        Category::Usb,
        Category::Cameras,
    ];

    for category in categories {
        let rows: Vec<&CheckResult> = dash
            .results
            .values()
            .filter(|r| r.category == category)
            .collect();
        if rows.is_empty() {
            continue;
        }

        let counts = count_results(rows.iter().copied());
        let mut banner = vec![
            Span::styled(" ▌ ", Style::default().fg(Color::Cyan)),
            Span::styled(
                category.label(),
                Style::default()
                    .fg(Color::Cyan)
                    .add_modifier(Modifier::BOLD),
            ),
        ];
        if counts.fail > 0 {
            banner.push(Span::raw("    "));
            banner.push(Span::styled(
                format!("✗ {} fail", counts.fail),
                Style::default()
                    .fg(Color::Red)
                    .add_modifier(Modifier::BOLD),
            ));
        }
        if counts.warn > 0 {
            banner.push(Span::raw("    "));
            banner.push(Span::styled(
                format!("⚠ {} warn", counts.warn),
                Style::default().fg(Color::Yellow),
            ));
        }
        if counts.pending > 0 {
            banner.push(Span::raw("    "));
            banner.push(Span::styled(
                format!("{} {} pending", spinner_frame(tick), counts.pending),
                Style::default().fg(Color::DarkGray),
            ));
        }
        lines.push(Line::from(banner));

        let current_ids: &[usize] = dash
            .steps
            .current_plan()
            .map(|p| p.row_ids.as_slice())
            .unwrap_or(&[]);
        for r in rows {
            let (icon, color) = outcome_marker(r.outcome, tick);
            let is_current = current_ids.contains(&r.id);
            let cursor_marker = if is_current { "▶ " } else { "  " };
            let name_style = if is_current {
                Style::default().add_modifier(Modifier::BOLD).fg(Color::White)
            } else {
                Style::default()
            };
            lines.push(Line::from(vec![
                Span::raw("  "),
                Span::styled(
                    cursor_marker,
                    Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
                ),
                Span::styled(
                    icon,
                    Style::default().fg(color).add_modifier(Modifier::BOLD),
                ),
                Span::raw("  "),
                Span::styled(
                    format!("{:<width$}", r.name, width = NAME_WIDTH),
                    name_style,
                ),
                Span::raw("  "),
                Span::styled(r.summary.clone(), summary_style(r.outcome)),
            ]));
        }
        lines.push(Line::from(""));
    }

    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::DarkGray));
    f.render_widget(Paragraph::new(lines).block(block), area);
}

fn draw_footer(f: &mut Frame, area: Rect, dash: &Dashboard) {
    let line = if dash.repair.visible {
        Line::from(vec![
            keyhint("↑↓"),
            Span::raw(" select   "),
            keyhint("Enter"),
            Span::raw(" run step   "),
            keyhint("Esc"),
            Span::raw(" close guide"),
        ])
    } else {
        Line::from(vec![
            keyhint("R"),
            Span::raw(" restart   "),
            keyhint("b"),
            Span::raw(" bring up XCP   "),
            keyhint("d"),
            Span::raw(" debug mode   "),
            keyhint("f"),
            Span::raw(" repair guide   "),
            keyhint("Esc"),
            Span::raw(" back   "),
            keyhint("q"),
            Span::raw(" quit"),
        ])
    };
    f.render_widget(Paragraph::new(line).alignment(Alignment::Center), area);
}

fn draw_repair_overlay(f: &mut Frame, dash: &Dashboard, tick: u64) {
    let area = centered_rect(70, 70, f.area());
    f.render_widget(Clear, area);

    let problem_failing = dash
        .results
        .values()
        .any(|r| r.name == dash.repair.kind.problem_check_name() && r.outcome == Outcome::Fail);

    let mut lines: Vec<Line> = Vec::new();
    let header = if problem_failing {
        Span::styled(
            format!("✗ {} is failing — pick a repair step", dash.repair.kind.label()),
            Style::default().fg(Color::Red).add_modifier(Modifier::BOLD),
        )
    } else {
        Span::styled(
            format!("{} is currently OK — repair steps available anyway", dash.repair.kind.label()),
            Style::default().fg(Color::DarkGray),
        )
    };
    lines.push(Line::from(header));
    lines.push(Line::from(""));

    for (i, step) in dash.repair.steps.iter().enumerate() {
        let selected = i == dash.repair.cursor;
        let is_running = dash.repair.running_step == Some(i);
        let is_inspect = matches!(step.action, RepairAction::Inspect);
        let (icon, color) = if is_running {
            (spinner_frame(tick).to_string(), Color::Cyan)
        } else {
            match (&dash.repair.status[i], is_inspect) {
                (_, true) => ("⚙".into(), Color::Yellow),
                (Some(RepairStatus::Ok(_)), false) => ("✓".into(), Color::Green),
                (Some(RepairStatus::Failed(_)), false) => ("✗".into(), Color::Red),
                (None, false) => ("$".into(), Color::Cyan),
            }
        };
        let cursor_marker = if selected { "▶ " } else { "  " };
        let label_style = if selected {
            Style::default().add_modifier(Modifier::BOLD).fg(Color::White)
        } else {
            Style::default()
        };
        let kind_tag = if is_inspect { "[hardware]" } else { "[software]" };
        let kind_tag_color = if is_inspect { Color::Yellow } else { Color::Cyan };
        lines.push(Line::from(vec![
            Span::styled(
                format!("{}{}  ", cursor_marker, icon),
                Style::default().fg(color).add_modifier(Modifier::BOLD),
            ),
            Span::styled(format!("{}. {}", i + 1, step.label), label_style),
            Span::raw("  "),
            Span::styled(
                kind_tag.to_string(),
                Style::default().fg(kind_tag_color),
            ),
        ]));
        for detail_line in step.detail.lines() {
            lines.push(Line::from(vec![
                Span::raw("       "),
                Span::styled(
                    detail_line.to_string(),
                    Style::default().fg(Color::DarkGray),
                ),
            ]));
        }
        if let Some(status) = &dash.repair.status[i] {
            let (msg_color, msg) = match status {
                RepairStatus::Ok(s) => (Color::Green, s.as_str()),
                RepairStatus::Failed(s) => (Color::Red, s.as_str()),
            };
            lines.push(Line::from(vec![
                Span::raw("       "),
                Span::styled(msg.to_string(), Style::default().fg(msg_color)),
            ]));
        }
        // Sub-checks are informational here (hardware items the user verifies
        // on the bench). The standalone guides view ticks them off; this
        // overlay just lists them so the bullet content stays visible while
        // the user runs the software fallbacks at the bottom.
        for sub in &step.checks {
            lines.push(Line::from(vec![
                Span::raw("       "),
                Span::styled("□ ", Style::default().fg(Color::DarkGray)),
                Span::raw(sub.label.to_string()),
            ]));
            if let Some(extra) = sub.detail {
                lines.push(Line::from(vec![
                    Span::raw("           "),
                    Span::styled(
                        extra.to_string(),
                        Style::default().fg(Color::DarkGray),
                    ),
                ]));
            }
        }
        lines.push(Line::from(""));
    }

    let title = format!(" Repair guide — {} ", dash.repair.kind.label());
    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::Cyan))
        .title(Span::styled(
            title,
            Style::default().add_modifier(Modifier::BOLD),
        ));

    f.render_widget(
        Paragraph::new(lines).block(block).wrap(Wrap { trim: false }),
        area,
    );
}

fn centered_rect(percent_x: u16, percent_y: u16, area: Rect) -> Rect {
    let v = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - percent_y) / 2),
            Constraint::Percentage(percent_y),
            Constraint::Percentage((100 - percent_y) / 2),
        ])
        .split(area);
    Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - percent_x) / 2),
            Constraint::Percentage(percent_x),
            Constraint::Percentage((100 - percent_x) / 2),
        ])
        .split(v[1])[1]
}

fn outcome_marker(o: Outcome, tick: u64) -> (String, Color) {
    match o {
        Outcome::Ok => ("✓".into(), Color::Green),
        Outcome::Warn => ("⚠".into(), Color::Yellow),
        Outcome::Fail => ("✗".into(), Color::Red),
        Outcome::Pending => (spinner_frame(tick).into(), Color::DarkGray),
    }
}

fn summary_style(o: Outcome) -> Style {
    match o {
        Outcome::Fail => Style::default().fg(Color::Red),
        Outcome::Warn => Style::default().fg(Color::Yellow),
        Outcome::Pending => Style::default().fg(Color::DarkGray),
        Outcome::Ok => Style::default(),
    }
}

#[derive(Default)]
struct Counts {
    ok: usize,
    warn: usize,
    fail: usize,
    pending: usize,
}

fn count_results<'a>(rs: impl Iterator<Item = &'a CheckResult>) -> Counts {
    let mut c = Counts::default();
    for r in rs {
        match r.outcome {
            Outcome::Ok => c.ok += 1,
            Outcome::Warn => c.warn += 1,
            Outcome::Fail => c.fail += 1,
            Outcome::Pending => c.pending += 1,
        }
    }
    c
}
