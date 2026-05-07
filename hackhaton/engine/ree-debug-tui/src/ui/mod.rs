// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

pub mod dashboard;
pub mod guides;
pub mod menu;
pub mod pick;

use ratatui::{
    style::{Color, Modifier, Style},
    text::Span,
    Frame,
};

use crate::app::{App, Stage};

pub const SPINNER_FRAMES: &[&str] = &["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

pub fn draw(f: &mut Frame, app: &App, tick: u64) {
    match &app.stage {
        Stage::Menu(m) => menu::draw(f, m),
        Stage::Picking(picker) => pick::draw(f, picker, tick),
        Stage::Guides(view) => guides::draw(f, view, tick),
        Stage::Dashboard(dash) => dashboard::draw(f, dash, tick),
    }
}

pub fn keyhint(key: &str) -> Span<'_> {
    Span::styled(
        format!(" {} ", key),
        Style::default()
            .bg(Color::DarkGray)
            .fg(Color::White)
            .add_modifier(Modifier::BOLD),
    )
}

pub fn spinner_frame(tick: u64) -> &'static str {
    SPINNER_FRAMES[(tick as usize) % SPINNER_FRAMES.len()]
}
