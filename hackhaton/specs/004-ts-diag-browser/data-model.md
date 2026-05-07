# Phase 1 — Data Model

This is the source of truth for the in-memory backend types, the WebSocket
message envelopes, and the frontend Zod schemas. Everything that crosses a
process / language boundary is mirrored on both sides; everything purely
internal is documented once.

For each entity, the table below names the **backend (Python / Pydantic)**
type, the **frontend (TypeScript / Zod)** type if one exists, and a brief
shape. Field-by-field details follow each table.

## 1. Live diagnostic surface state (backend in-memory only)

These types live entirely in the FastAPI process; they are not serialized
across the wire as-is. They drive what gets pushed onto the WebSocket.

### `LiveDiagnosticSession` (backend)

One per active WebSocket. Owns the ssh subprocess and the per-session tasks.

| Field | Type | Notes |
|---|---|---|
| `session_id` | `uuid.UUID` | Server-assigned. Surfaced to the frontend in the `ready` envelope so logs can correlate. |
| `operator_slug` | `str` | From `X-Vay-User` (the existing 001 SSO header). Used in backend logs only. |
| `host_id` | `str` | Inventory id (e.g., `ts-de-ber-00005`). |
| `host_address` | `str` | Resolved by the inventory loader from the `ansible_host` attribute of the chosen host. Passed to `ssh` as the connection target. |
| `user_override` | `str | None` | Optional `user@` override from the dialog. `None` means "let `~/.ssh/config` decide". |
| `port_override` | `int | None` | Optional port override. `None` means default. |
| `state` | `Literal["connecting","connected","lost","closed"]` | Session lifecycle. `lost` triggers FR-017 banner; `closed` is terminal. |
| `started_at` | `datetime` | UTC. Set on entry to `connecting`. |
| `last_frame_at` | `datetime | None` | Updated on every successfully decoded frame. Used to drive the 10 s stall heartbeat (R6). |
| `proc` | `asyncio.subprocess.Process | None` | The `ssh ... candump` subprocess handle. |
| `tasks` | `list[asyncio.Task]` | The reader + decoder + outbound-fanout tasks. Tracked for clean teardown. |
| `outbound` | `asyncio.Queue[ServerEnvelope]` | Bounded (`maxsize=512`); see FR-018. Newest-wins on overflow. |
| `filter` | `LiveFilter` | Current channel + signal-name filter selections. Mutates on `set_filter` / `set_channel`. |
| `paused` | `bool` | When True, `signal_update` envelopes are still produced server-side but suppressed from the outbound queue (FR-015). The pause counter is exposed as the `pause_buffer_count` of `status` envelopes. |
| `errq_aggregator` | `ErrqAggregator` | Per-session aggregator (R4) so concurrent sessions don't share buffers. |
| `errq_state` | `ErrqStateTracker` | Active/passive lifecycle tracker (port from desktop tool). |
| `errq_model` | `ErrqModel | None` | Shared read-only handle to the loaded errq model; `None` means degraded mode. |

State transitions:

```text
            ┌─ connect_ok ──┐
connecting ─┤               ├─→ connected ─→ stalled (≥10s) → lost
            └─ connect_err ─┴─→ lost
                                       │
                                       └─→ ws_close / explicit_close → closed
```

### `LiveFilter` (backend in-memory; mirrored as `LiveFilter` in TS)

| Field | Type | Notes |
|---|---|---|
| `channel` | `Literal["A","B","both"]` | Default `"both"`. |
| `signal_name_substring` | `str` | Case-insensitive. Empty string = no filter. |
| `raw_frames_enabled` | `bool` | Default `False`. When True, server emits `raw_frame` envelopes. |

### `ErrqAggregator` (backend in-memory)

Ported from `TS_diagnostic_tool/errq_aggregator.py`. Same shape; namespace
adjusted to `vayobd.live.errq_aggregator`.

| Field | Type | Notes |
|---|---|---|
| `_channels` | `dict[str, _ChannelBuffer]` | Two entries (`A`, `B`); each is a 64-byte `bytearray`. |

Methods (unchanged from desktop tool):
- `ingest(signals: dict[str, int]) -> set[str]` — returns touched channels.
- `snapshot(channel: str) -> bytes` — returns the current 64-byte buffer.
- `reset() -> None` — zeros both channels.

### `ErrqStateTracker` (backend in-memory)

Ported from `TS_diagnostic_tool/errq_state.py`. Holds the active/passive
lifecycle (FR-011) — an error becomes "passive" the first cycle after its
bit clears, and is removed from the panel after a 2 s grace.

| Field | Type | Notes |
|---|---|---|
| `_active` | `dict[(channel, byte, bit), datetime]` | First-seen timestamps. |
| `_pending_clear` | `dict[(channel, byte, bit), datetime]` | "Bit was set last cycle, not this cycle" — removed if still absent after 2 s. |

### `ErrqModel` (backend in-memory)

The runtime handle to the loaded errq model. Loaded once at startup from
the configured `~/GitHub/ree-reecu` clone. Wraps the desktop tool's
`errq.build_model("ts")` call but encapsulates the module-level globals so
two concurrent sessions don't race.

| Field | Type | Notes |
|---|---|---|
| `model` | `Any` | The `errq.build_model("ts")` return value (~220-error model). |
| `module` | `ModuleType` | The dynamically-imported `errq` module (needed for `decode_errors`). |
| `loaded_at` | `datetime` | UTC. Used in degraded-mode messaging. |
| `source_path` | `Path` | Where it was loaded from (for backend logs + degraded-mode UI hint). |

If load fails, the backend keeps `errq_model = None` on every session and
US2 / US4 fall into degraded mode (FR-012) — the panel shows raw bytes per
channel.

## 2. WebSocket message envelopes (cross-process; mirrored frontend)

Full JSON examples in `contracts/websocket.md`. The shape is a discriminated
union on `kind`. Both sides validate (Pydantic on backend, Zod on frontend);
mismatched envelopes are dropped and counted in a "schema_errors" gauge.

### Server → client envelopes

| `kind` | Pydantic / Zod type | Purpose |
|---|---|---|
| `ready` | `ReadyEnvelope` | First message after WebSocket accept. Includes `session_id`, `host_id`, `errq_loaded` flag, server build SHA. |
| `status` | `StatusEnvelope` | State changes (`connecting → connected`, `connected → lost`). Includes `state`, optional `reason` and `ssh_stderr_first_line`. |
| `signal_update` | `SignalUpdateEnvelope` | Batched decoded values (one envelope ≈ 50–200 frames). Includes `channel`, `at_ms` (server-side ms timestamp), and a list of `(name, value, unit)` triples — only signals whose value *changed* since the previous envelope. |
| `errq_update` | `ErrqUpdateEnvelope` | Diff against the previous active set: `appeared: ErrqEntry[]`, `disappeared: (channel, byte, bit)[]`. Empty lists permitted. |
| `raw_frame` | `RawFrameEnvelope` | Pass-through CAN frame for the optional log. Only emitted when `raw_frames_enabled` is true. |
| `error` | `ErrorEnvelope` | Backend-side error that doesn't kill the session — e.g. DBC missing for a frame, errq model degraded. Includes `code` and `message`. |

### Client → server envelopes

| `kind` | Pydantic / Zod type | Effect |
|---|---|---|
| `set_filter` | `SetFilterEnvelope` | Update `LiveFilter.signal_name_substring`. |
| `set_channel` | `SetChannelEnvelope` | Update `LiveFilter.channel`. |
| `pause` | `PauseEnvelope` | `paused = true`. Server keeps decoding but stops sending `signal_update`. |
| `resume` | `ResumeEnvelope` | `paused = false`. Server flushes a single coalesced `signal_update` of the latest values, then resumes streaming. |
| `clear` | `ClearEnvelope` | Server sends a single `signal_update` with all current signals set to a sentinel `null` value, and resets the errq aggregator buffers (`reset()`). |
| `toggle_raw_frames` | `ToggleRawFramesEnvelope` | Update `LiveFilter.raw_frames_enabled`. |

## 3. Domain types (mirrored both sides)

These are referenced inside envelopes above.

### `DecodedSignal`

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | DBC signal name. |
| `value` | `float | bool | str | None` | The decoded value. `None` means "unknown" (DBC missing for the frame). |
| `unit` | `str | None` | DBC unit if any. |
| `channel` | `Literal["A","B","unknown"]` | Inferred from the DBC message owner. `unknown` covers signals not classified into A/B. |
| `can_id` | `int` | Source CAN id (decimal). |
| `at_ms` | `int` | Server-side ms timestamp of the source frame. |

### `ErrqEntry`

Mirrors `errq_bridge.ErrqResult` from the desktop tool.

| Field | Type | Notes |
|---|---|---|
| `code` | `int` | Bit value (1, 2, 4, …) that triggered this error. |
| `name` | `str | None` | Symbolic error id from the CSV. |
| `description` | `str` | Human-readable description (`name` if CSV description column is empty). |
| `severity` | `Literal["info","warn","error","critical"] | None` | Best-effort severity from group membership. |
| `channel` | `Literal["A","B"]` | Channel of the source ERRQ buffer. |
| `byte` | `int` | 1-based byte index. |
| `bit` | `int` | Bit index within the byte. |
| `first_seen_ms` | `int` | When the error first transitioned to active. |
| `last_seen_ms` | `int` | Last `signal_update` cycle in which it was still active. |

### `RawFrame`

| Field | Type | Notes |
|---|---|---|
| `at_ms` | `int` | Server-side ms timestamp. |
| `can_id` | `int` | Decimal CAN id. |
| `dlc` | `int` | Data length code. |
| `payload_hex` | `str` | Raw payload, lowercase hex, no separators. |

## 4. Settings deltas (TOML on disk + Pydantic + Zod)

Adds three keys to `~/.config/vayobd/settings.toml` (existing file from
002). Backend reads on startup; frontend reads via the existing
`/api/settings` route.

| Key | Type | Default | Notes |
|---|---|---|---|
| `developer_mode` | `bool` | `false` | Drives FR-001 / FR-002 visibility. |
| `ree_reecu_path` | `str` | `~/GitHub/ree-reecu` | Where the errq CSVs live. Resolved at backend startup; degraded mode if missing. |
| `dbc_path` | `str` | `~/GitHub/ree-reecu/.../ts.dbc` (TBD: confirm exact path with team) | Where the TS DBC lives. Used by `cantools.database.load_file`. |

## 5. Validation rules

- `host_id` MUST resolve to an entry in the in-scope inventory (FR-004 +
  FR-005). If not, the WebSocket handshake closes with code `1008` ("policy
  violation") and a JSON body `{ "error": "host_out_of_scope" }`.
- `port_override` (if set) MUST be an integer in `[1, 65535]`.
- `signal_name_substring` MUST be ≤ 128 chars after trim. Empty string is
  the no-filter sentinel.
- All numeric timestamps are server-side ms since UNIX epoch (`int`); the
  frontend uses `Date.now()`-relative deltas only for UI animations.
- `bytes` payloads are transmitted as lowercase hex strings (no `0x`
  prefix), since JSON has no native bytes type. The backend's `RawFrame`
  type is the canonical bytes-friendly form.

## 6. Out-of-scope (deferred to v2 if needed)

- Per-operator persisted "live history" or "session replay" — FR-018 +
  spec assumptions explicitly defer this.
- Per-host concurrency caps at the testbed side — FR-019 assumes the
  testbed permits multiple ssh sessions; if a hard cap surfaces, this
  document gets a `MAX_CONCURRENT_SESSIONS_PER_HOST` field on `ErrqModel`
  or a new `HostQuota` entity.
- Multiplexed signals beyond what cantools handles natively — covered by
  cantools 39+.
