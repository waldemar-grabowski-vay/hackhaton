// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

use crate::app::Menu;
use crate::ui::keyhint;

const VAY_LOGO: &[&str] = &[
    "██╗   ██╗ █████╗ ██╗   ██╗",
    "██║   ██║██╔══██╗╚██╗ ██╔╝",
    "██║   ██║███████║ ╚████╔╝ ",
    "╚██╗ ██╔╝██╔══██║  ╚██╔╝  ",
    " ╚████╔╝ ██║  ██║   ██║   ",
    "  ╚═══╝  ╚═╝  ╚═╝   ╚═╝   ",
];

const LOGO_TAGLINE: &str = "ree-debug-tui · testbed observability";

pub fn draw(f: &mut Frame, menu: &Menu) {
    let area = f.area();
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(3), Constraint::Min(0), Constraint::Length(1)])
        .split(area);

    draw_header(f, chunks[0]);
    draw_body(f, chunks[1], menu);
    draw_footer(f, chunks[2]);
}

fn draw_header(f: &mut Frame, area: Rect) {
    let block = Block::default()
        .borders(Borders::ALL)
        .title(Span::styled(
            " ree-debug-tui ",
            Style::default().add_modifier(Modifier::BOLD),
        ))
        .border_style(Style::default().fg(Color::DarkGray));
    let line = Line::from(Span::styled(
        "what would you like to do?",
        Style::default().add_modifier(Modifier::BOLD),
    ));
    f.render_widget(
        Paragraph::new(line).alignment(Alignment::Center).block(block),
        area,
    );
}

fn draw_body(f: &mut Frame, area: Rect, menu: &Menu) {
    let block = Block::default()
        .borders(Borders::ALL)
        .title(Span::styled(
            " main menu ",
            Style::default().add_modifier(Modifier::BOLD),
        ))
        .border_style(Style::default().fg(Color::DarkGray));
    let inner = block.inner(area);
    f.render_widget(block, area);

    // Each entry takes 3 lines (label, detail, blank); we want at least
    // that plus a top-pad. Logo block is logo rows + tagline + blank.
    let logo_height = (VAY_LOGO.len() + 2) as u16;
    let menu_height = (menu.entries().len() * 3 + 2) as u16;
    let show_logo = inner.height >= logo_height + menu_height + 1;

    let chunks = if show_logo {
        Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(1),
                Constraint::Length(logo_height),
                Constraint::Length(1),
                Constraint::Min(0),
            ])
            .split(inner)
    } else {
        Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Length(1), Constraint::Min(0)])
            .split(inner)
    };

    if show_logo {
        draw_logo(f, chunks[1]);
        draw_menu_entries(f, chunks[3], menu);
    } else {
        draw_menu_entries(f, chunks[1], menu);
    }
}

fn draw_logo(f: &mut Frame, area: Rect) {
    let mut lines: Vec<Line> = VAY_LOGO
        .iter()
        .map(|row| {
            Line::from(Span::styled(
                (*row).to_string(),
                Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
            ))
        })
        .collect();
    lines.push(Line::from(""));
    lines.push(Line::from(Span::styled(
        LOGO_TAGLINE,
        Style::default().fg(Color::DarkGray),
    )));
    f.render_widget(Paragraph::new(lines).alignment(Alignment::Center), area);
}

fn draw_menu_entries(f: &mut Frame, area: Rect, menu: &Menu) {
    let mut lines: Vec<Line> = Vec::new();
    for (i, entry) in menu.entries().iter().enumerate() {
        let selected = i == menu.cursor;
        let cursor_marker = if selected { "▶ " } else { "  " };
        let label_style = if selected {
            Style::default()
                .fg(Color::Black)
                .bg(Color::Green)
                .add_modifier(Modifier::BOLD)
        } else {
            Style::default().add_modifier(Modifier::BOLD)
        };
        lines.push(Line::from(vec![
            Span::raw("    "),
            Span::styled(cursor_marker, Style::default().fg(Color::Green)),
            Span::styled(format!(" {} ", entry.label()), label_style),
        ]));
        lines.push(Line::from(vec![
            Span::raw("       "),
            Span::styled(entry.detail(), Style::default().fg(Color::DarkGray)),
        ]));
        lines.push(Line::from(""));
    }
    f.render_widget(Paragraph::new(lines), area);
}

fn draw_footer(f: &mut Frame, area: Rect) {
    let line = Line::from(vec![
        keyhint("↑↓"),
        Span::raw(" or "),
        keyhint("k j"),
        Span::raw(" move    "),
        keyhint("Enter"),
        Span::raw(" select    "),
        keyhint("q/Esc"),
        Span::raw(" quit"),
    ]);
    f.render_widget(Paragraph::new(line).alignment(Alignment::Center), area);
}
