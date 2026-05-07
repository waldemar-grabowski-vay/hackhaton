// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, ListState, Paragraph},
    Frame,
};

use crate::app::{Picker, PickerAction};
use ree_debug_engine::inventory::HostKind;
use ree_debug_engine::ping::PingStatus;
use crate::ui::{keyhint, spinner_frame};

pub fn draw(f: &mut Frame, picker: &Picker, tick: u64) {
    let area = f.area();
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),
            Constraint::Min(0),
            Constraint::Length(1),
        ])
        .split(area);

    // Header
    let header_block = Block::default()
        .borders(Borders::ALL)
        .title(Span::styled(
            " ree-debug-tui ",
            Style::default().add_modifier(Modifier::BOLD),
        ))
        .border_style(Style::default().fg(Color::DarkGray));
    let ts_count = picker.hosts.iter().filter(|h| h.kind == HostKind::Ts).count();
    let ve_count = picker.hosts.iter().filter(|h| h.kind == HostKind::Ve).count();
    let (online, offline, probing, _unknown) = picker.ping_counts();
    let prompt = match picker.action {
        PickerAction::Debug => "pick a DE TS or VE — debug",
        PickerAction::Guides => "pick a DE TS or VE — repair guide",
    };
    let mut header_spans = vec![
        Span::styled(
            prompt,
            Style::default().add_modifier(Modifier::BOLD),
        ),
        Span::raw("    "),
        Span::styled(
            " TS ",
            Style::default()
                .bg(Color::Cyan)
                .fg(Color::Black)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(format!(" {}", ts_count), Style::default().fg(Color::Cyan)),
        Span::raw("   "),
        Span::styled(
            " VE ",
            Style::default()
                .bg(Color::Magenta)
                .fg(Color::Black)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(format!(" {}", ve_count), Style::default().fg(Color::Magenta)),
        Span::raw("        "),
        Span::styled(
            format!("● {} online", online),
            Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
        ),
        Span::raw("   "),
        Span::styled(
            format!("● {} offline", offline),
            Style::default().fg(Color::Red).add_modifier(Modifier::BOLD),
        ),
    ];
    if probing > 0 {
        header_spans.push(Span::raw("   "));
        header_spans.push(Span::styled(
            format!("{} {} probing", spinner_frame(tick), probing),
            Style::default().fg(Color::Yellow),
        ));
    }
    let header_line = Line::from(header_spans);
    f.render_widget(
        Paragraph::new(header_line)
            .alignment(Alignment::Center)
            .block(header_block),
        chunks[0],
    );

    // Body: list (or error)
    if let Some(err) = &picker.error {
        let p = Paragraph::new(format!(
            "inventory error: {}\n\nexpected at:\n  ~/GitHub/ree-vehicle-configs/org/vay/inventory.yaml",
            err
        ))
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title(Span::styled(
                    " Error ",
                    Style::default()
                        .fg(Color::Red)
                        .add_modifier(Modifier::BOLD),
                ))
                .border_style(Style::default().fg(Color::Red)),
        );
        f.render_widget(p, chunks[1]);
    } else if picker.hosts.is_empty() {
        let p = Paragraph::new("inventory is empty")
            .block(Block::default().borders(Borders::ALL));
        f.render_widget(p, chunks[1]);
    } else {
        let mut items: Vec<ListItem> = Vec::with_capacity(picker.hosts.len());
        for h in &picker.hosts {
            let badge_bg = match h.kind {
                HostKind::Ts => Color::Cyan,
                HostKind::Ve => Color::Magenta,
            };
            let badge = Span::styled(
                format!(" {} ", h.kind.tag()),
                Style::default()
                    .bg(badge_bg)
                    .fg(Color::Black)
                    .add_modifier(Modifier::BOLD),
            );
            let status = picker.status.get(&h.name).copied().unwrap_or(PingStatus::Unknown);
            let status_marker = ping_marker(status, tick);
            let name = Span::styled(
                format!("{:<26}", h.name),
                Style::default().add_modifier(Modifier::BOLD),
            );
            let ip = Span::styled(
                h.ansible_host.clone().unwrap_or_else(|| "?".into()),
                Style::default().fg(Color::DarkGray),
            );
            items.push(ListItem::new(Line::from(vec![
                badge,
                Span::raw(" "),
                status_marker,
                Span::raw(" "),
                name,
                Span::raw("  "),
                ip,
            ])));
        }
        let title = Span::styled(
            format!(" Hosts ({}) ", picker.hosts.len()),
            Style::default().add_modifier(Modifier::BOLD),
        );
        let list = List::new(items)
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .title(title)
                    .border_style(Style::default().fg(Color::DarkGray)),
            )
            .highlight_style(
                Style::default()
                    .bg(Color::Green)
                    .fg(Color::Black)
                    .add_modifier(Modifier::BOLD),
            )
            .highlight_symbol("▶ ");
        let mut state = ListState::default();
        state.select(Some(picker.cursor));
        f.render_stateful_widget(list, chunks[1], &mut state);
    }

    // Footer
    let line = Line::from(vec![
        keyhint("↑↓"),
        Span::raw(" or "),
        keyhint("k j"),
        Span::raw(" move    "),
        keyhint("Enter"),
        Span::raw(" connect    "),
        keyhint("Esc"),
        Span::raw(" back    "),
        keyhint("q"),
        Span::raw(" quit"),
    ]);
    f.render_widget(
        Paragraph::new(line).alignment(Alignment::Center),
        chunks[2],
    );
}

fn ping_marker(status: PingStatus, tick: u64) -> Span<'static> {
    match status {
        PingStatus::Online => Span::styled("●", Style::default().fg(Color::Green)),
        PingStatus::Offline => Span::styled("●", Style::default().fg(Color::Red)),
        PingStatus::Probing => {
            Span::styled(spinner_frame(tick).to_string(), Style::default().fg(Color::Yellow))
        }
        PingStatus::Unknown => Span::styled("·", Style::default().fg(Color::DarkGray)),
    }
}
