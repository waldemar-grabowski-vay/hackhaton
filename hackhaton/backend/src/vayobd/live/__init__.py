"""Live diagnostic backend module (004).

Ports the IP from `TS_diagnostic_tool/` (PyQt6 desktop) into a
WebSocket-driven backend module:

- `errq_aggregator` — stitches `TS_Ch[AB]_ERRQ_Byte01..64` signals into
  64-byte buffers per channel.
- `errq_state` — Active/Passive lifecycle tracker.
- `errq_loader` — loads the local `errq` Python module from the operator's
  `~/GitHub/ree-reecu` clone; encapsulates the desktop tool's
  module-level globals so concurrent sessions don't race.
- `dbc_decoder` — wraps `cantools` for per-frame decoding; falls back to
  glob-search across the `ree-reecu` clone when no explicit `dbc_path`
  is configured.
- `candump_runner` — async subprocess wrapper around the operator's
  local `ssh` binary streaming `candump`.
- `session` — per-WebSocket state machine that orchestrates the runner,
  decoder, aggregator, and tracker, and emits envelopes.
- `live_models` — Pydantic envelope models matching `contracts/websocket.md`.
- `ws_router` — FastAPI WebSocket route at `/api/live/{host_id}/ws`.
"""
