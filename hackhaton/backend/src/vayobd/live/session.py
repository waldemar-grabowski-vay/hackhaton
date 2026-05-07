"""LiveDiagnosticSession state machine (T022 — Phase 3 / US1 stub).

One per active WebSocket. Owns the candump runner, decoder, aggregator,
state tracker, outbound bounded queue, and lifecycle. Implementation
lands in T022 (Phase 3, US1).
"""

from __future__ import annotations
