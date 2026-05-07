// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph, Wrap},
    Frame,
};

use crate::app::{GuidesView, RepairStatus};
use ree_debug_engine::inventory::HostKind;
use crate::repair::{Diagram, DiagramSpan, RepairAction, RepairStep, WireColor};
use crate::ui::{keyhint, spinner_frame};

pub fn draw(f: &mut Frame, view: &GuidesView, tick: u64) {
    let area = f.area();
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(3), Constraint::Min(0), Constraint::Length(1)])
        .split(area);

    draw_header(f, chunks[0], view);
    draw_page(f, chunks[1], view, tick);
    draw_footer(f, chunks[2], view);
}

fn draw_header(f: &mut Frame, area: Rect, view: &GuidesView) {
    let block = Block::default()
        .borders(Borders::ALL)
        .title(Span::styled(
            " ree-debug-tui — repair guides ",
            Style::default().add_modifier(Modifier::BOLD),
        ))
        .border_style(Style::default().fg(Color::DarkGray));

    let flavor_color = match view.flavor {
        HostKind::Ts => Color::Cyan,
        HostKind::Ve => Color::Magenta,
    };
    let page_idx = view.current_target().map(|t| t.step + 1).unwrap_or(1);
    let total = view.steps.len().max(1);

    let mut spans = vec![
        Span::styled(
            view.kind.label(),
            Style::default().add_modifier(Modifier::BOLD),
        ),
        Span::raw("    flavor: "),
        Span::styled(
            format!(" {} ", view.flavor.tag()),
            Style::default()
                .bg(flavor_color)
                .fg(Color::Black)
                .add_modifier(Modifier::BOLD),
        ),
        Span::raw("    "),
        Span::styled(
            format!("page {} / {}", page_idx, total),
            Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
        ),
        Span::raw("    "),
    ];
    match &view.host {
        Some(host) => {
            spans.push(Span::raw("host: "));
            spans.push(Span::styled(
                host.clone(),
                Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
            ));
        }
        None => {
            spans.push(Span::styled(
                "(local walkthrough)",
                Style::default().fg(Color::DarkGray),
            ));
        }
    }
    f.render_widget(
        Paragraph::new(Line::from(spans))
            .alignment(Alignment::Center)
            .block(block),
        area,
    );
}

fn draw_page(f: &mut Frame, area: Rect, view: &GuidesView, tick: u64) {
    let target = match view.current_target() {
        Some(t) => t,
        None => return,
    };
    let step_idx = target.step;
    let step = match view.steps.get(step_idx) {
        Some(s) => s,
        None => return,
    };

    // Outer page block carries the step's title.
    let page_block = Block::default()
        .borders(Borders::ALL)
        .title(Span::styled(
            format!(" Step {} / {} — {} ", step_idx + 1, view.steps.len(), step.label),
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        ))
        .border_style(Style::default().fg(Color::DarkGray));
    let inner = page_block.inner(area);
    f.render_widget(page_block, area);

    // Split into: tag + description (top), diagram (middle, optional),
    // sub-checks (bottom).
    let detail_height = 1 + step.detail.lines().count() as u16 + 1;
    let diagram_height = step
        .diagram
        .as_ref()
        .map(|d| d.lines.len() as u16 + 3)
        .unwrap_or(0);
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(detail_height),
            Constraint::Length(diagram_height),
            Constraint::Min(0),
        ])
        .split(inner);

    draw_step_detail(f, chunks[0], step, view, tick);
    if step.diagram.is_some() {
        draw_diagram(f, chunks[1], step.diagram.as_ref().unwrap());
    }
    draw_step_checklist(f, chunks[2], step, step_idx, view, target);
}

fn draw_step_detail(
    f: &mut Frame,
    area: Rect,
    step: &RepairStep,
    view: &GuidesView,
    tick: u64,
) {
    let mut lines: Vec<Line> = Vec::new();
    let step_idx = view.current_target().map(|t| t.step).unwrap_or(0);
    let is_running = view.running_step == Some(step_idx);
    let (kind_icon, kind_color, kind_tag) = match (&step.action, is_running) {
        (_, true) => (spinner_frame(tick), Color::Cyan, "running"),
        (RepairAction::Inspect, false) => match &view.status[step_idx] {
            Some(RepairStatus::Ok(_)) => ("✓", Color::Green, "hardware"),
            Some(RepairStatus::Failed(_)) => ("✗", Color::Red, "hardware"),
            None => ("⚙", Color::Yellow, "hardware"),
        },
        (RepairAction::Command(_), false) => match &view.status[step_idx] {
            Some(RepairStatus::Ok(_)) => ("✓", Color::Green, "software"),
            Some(RepairStatus::Failed(_)) => ("✗", Color::Red, "software"),
            None => ("$", Color::Cyan, "software"),
        },
    };
    lines.push(Line::from(vec![
        Span::raw(" "),
        Span::styled(
            format!("{} ", kind_icon),
            Style::default().fg(kind_color).add_modifier(Modifier::BOLD),
        ),
        Span::styled(
            format!("[{}]", kind_tag),
            Style::default().fg(kind_color),
        ),
    ]));
    for detail_line in step.detail.lines() {
        lines.push(Line::from(vec![
            Span::raw(" "),
            Span::styled(
                detail_line.to_string(),
                Style::default().fg(Color::DarkGray),
            ),
        ]));
    }
    if let Some(status) = &view.status[step_idx] {
        let (msg_color, msg) = match status {
            RepairStatus::Ok(s) => (Color::Green, s.as_str()),
            RepairStatus::Failed(s) => (Color::Red, s.as_str()),
        };
        lines.push(Line::from(vec![
            Span::raw(" "),
            Span::styled(msg.to_string(), Style::default().fg(msg_color)),
        ]));
    }
    f.render_widget(
        Paragraph::new(lines).wrap(Wrap { trim: false }),
        area,
    );
}

fn draw_diagram(f: &mut Frame, area: Rect, diagram: &Diagram) {
    let diagram_block = Block::default()
        .borders(Borders::ALL)
        .title(Span::styled(
            format!(" {} ", diagram.title),
            Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
        ))
        .border_style(Style::default().fg(Color::DarkGray));
    let inner = diagram_block.inner(area);
    f.render_widget(diagram_block, area);

    let lines: Vec<Line> = diagram
        .lines
        .iter()
        .map(|spans| {
            Line::from(spans.iter().map(diagram_to_span).collect::<Vec<_>>())
        })
        .collect();
    f.render_widget(Paragraph::new(lines), inner);
}

fn diagram_to_span(s: &DiagramSpan) -> Span<'static> {
    let style = match s.color {
        WireColor::Default => Style::default(),
        WireColor::Black => Style::default().fg(Color::White), // pure black is invisible on dark bg
        WireColor::Red => Style::default().fg(Color::Red).add_modifier(Modifier::BOLD),
        WireColor::Blue => Style::default().fg(Color::Blue).add_modifier(Modifier::BOLD),
        WireColor::Brown => Style::default().fg(Color::Rgb(160, 82, 45)),
        WireColor::Yellow => Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
        WireColor::Green => Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
        WireColor::Gray => Style::default().fg(Color::Gray),
        WireColor::White => Style::default().fg(Color::White).add_modifier(Modifier::BOLD),
        WireColor::Pin => Style::default().add_modifier(Modifier::BOLD),
        WireColor::Note => Style::default().fg(Color::DarkGray),
    };
    Span::styled(s.text.to_string(), style)
}

fn draw_step_checklist(
    f: &mut Frame,
    area: Rect,
    step: &RepairStep,
    step_idx: usize,
    view: &GuidesView,
    target: crate::app::GuidesTarget,
) {
    let mut lines: Vec<Line> = Vec::new();

    // The step header itself is one cursor target. Show a clear "select to
    // bulk-tick" row at the top of the checklist.
    let header_selected = target.step == step_idx && target.sub.is_none();
    let header_marker = if header_selected { "▶ " } else { "  " };
    let header_style = if header_selected {
        Style::default().fg(Color::White).add_modifier(Modifier::BOLD)
    } else {
        Style::default().add_modifier(Modifier::BOLD)
    };
    lines.push(Line::from(vec![
        Span::styled(header_marker, Style::default().fg(Color::Green)),
        Span::styled("Mark whole step done", header_style),
        Span::raw("   "),
        Span::styled(
            "(Enter ticks the step + every sub-check)",
            Style::default().fg(Color::DarkGray),
        ),
    ]));
    if matches!(step.action, RepairAction::Command(_)) && header_selected {
        if let RepairAction::Command(cmd) = &step.action {
            lines.push(Line::from(""));
            for cmd_line in cmd.lines() {
                lines.push(Line::from(vec![
                    Span::raw("    "),
                    Span::styled(
                        cmd_line.to_string(),
                        Style::default().fg(Color::Yellow),
                    ),
                ]));
            }
        }
    }
    lines.push(Line::from(""));

    // Sub-checks.
    for (j, sub) in step.checks.iter().enumerate() {
        let sub_selected = target.step == step_idx && target.sub == Some(j);
        let sub_marker = if sub_selected { "▶ " } else { "  " };
        let sub_status = view
            .sub_status
            .get(step_idx)
            .and_then(|v| v.get(j))
            .and_then(|s| s.as_ref());
        let (sub_icon, sub_icon_color) = match sub_status {
            Some(RepairStatus::Ok(_)) => ("✓", Color::Green),
            Some(RepairStatus::Failed(_)) => ("✗", Color::Red),
            None => ("□", Color::DarkGray),
        };
        let sub_label_style = if sub_selected {
            Style::default().fg(Color::White).add_modifier(Modifier::BOLD)
        } else {
            Style::default()
        };
        lines.push(Line::from(vec![
            Span::styled(sub_marker, Style::default().fg(Color::Green)),
            Span::styled(
                format!("{} ", sub_icon),
                Style::default()
                    .fg(sub_icon_color)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled(sub.label.to_string(), sub_label_style),
        ]));
        if let Some(extra) = sub.detail {
            lines.push(Line::from(vec![
                Span::raw("    "),
                Span::styled(
                    extra.to_string(),
                    Style::default().fg(Color::DarkGray),
                ),
            ]));
        }
    }

    let block = Block::default()
        .borders(Borders::ALL)
        .title(Span::styled(
            " Checklist ",
            Style::default().add_modifier(Modifier::BOLD),
        ))
        .border_style(Style::default().fg(Color::DarkGray));
    f.render_widget(
        Paragraph::new(lines).block(block).wrap(Wrap { trim: false }),
        area,
    );
}

fn draw_footer(f: &mut Frame, area: Rect, view: &GuidesView) {
    let line = if view.host_attached() {
        Line::from(vec![
            keyhint("←→"),
            Span::raw(" page   "),
            keyhint("↑↓"),
            Span::raw(" item   "),
            keyhint("Enter"),
            Span::raw(" run/check   "),
            keyhint("[ ]"),
            Span::raw(" guide   "),
            keyhint("Esc"),
            Span::raw(" back   "),
            keyhint("q"),
            Span::raw(" quit"),
        ])
    } else {
        Line::from(vec![
            keyhint("←→"),
            Span::raw(" page   "),
            keyhint("↑↓"),
            Span::raw(" item   "),
            keyhint("Enter"),
            Span::raw(" check & next   "),
            keyhint("[ ]"),
            Span::raw(" guide   "),
            keyhint("Tab"),
            Span::raw(" TS/VE   "),
            keyhint("Esc"),
            Span::raw(" back   "),
            keyhint("q"),
            Span::raw(" quit"),
        ])
    };
    f.render_widget(Paragraph::new(line).alignment(Alignment::Center), area);
}
