# WebSocket contract: `/api/live/{host_id}/ws`

This is the wire-level contract for the Live diagnostic surface. The browser
opens one WebSocket per session; the connection carries both the streamed
diagnostic data (server → client) and the operator's runtime controls
(client → server). All messages are JSON, validated by Pydantic on the
server and Zod on the client.

## URL & handshake

- **Path**: `GET /api/live/{host_id}/ws` — HTTP upgrade to WebSocket.
- **Path param**: `host_id` — the inventory id (e.g. `ts-de-ber-00005`).
  MUST be in scope (Germany hosts only — FR-004); out-of-scope ids close
  the handshake with WebSocket close code `1008` and reason
  `host_out_of_scope`.
- **Headers**:
  - `X-Vay-User: <operator-slug>` — required (existing 001 SSO header).
    Missing closes the handshake with code `1008` reason `unauthorized`.
- **Query string**:
  - `user` — optional `user@` override for the SSH command (FR-003).
  - `port` — optional integer port override.
  - `developer_mode_check` — required `=1` query — the frontend MUST set
    this only when its local Developer-mode flag is on; the server
    cross-checks against the on-disk setting (FR-002).

If the operator's local Developer mode is off, the frontend MUST NOT open
this WebSocket; the server treats a missing `developer_mode_check=1` as
`developer_mode_off` and closes with `1008`.

## Envelope shape

Every message is a JSON object with two top-level keys:

```json
{
  "kind": "<one of the kinds below>",
  "payload": { ... }
}
```

Unknown `kind` values MUST be silently dropped by the receiver and counted
in a per-session `schema_errors` counter (surfaced through backend logs
only). This keeps both sides forward-compatible across small additions.

## Server → client messages

### `ready`

Sent once, immediately after the WebSocket is accepted and the SSH
subprocess has been spawned (state: `connecting`). Tells the client the
session is alive and what the server's initial state is.

```json
{
  "kind": "ready",
  "payload": {
    "session_id": "01HXXX...",
    "host_id": "ts-de-ber-00005",
    "errq_loaded": true,
    "errq_source_path": "/home/op/GitHub/ree-reecu",
    "dbc_loaded": true,
    "dbc_source_path": "/home/op/GitHub/ree-reecu/.../ts.dbc",
    "server_build": "abc123d"
  }
}
```

If `errq_loaded` is `false`, US2 / FR-012 degraded mode is in effect — the
frontend SHOULD render the errq panel's empty state with the explanatory
text and skip rendering decoded errors.

### `status`

Sent on every state transition.

```json
{
  "kind": "status",
  "payload": {
    "state": "connecting | connected | lost | closed",
    "reason": null,
    "ssh_stderr_first_line": null,
    "since_ms": 1714567890123,
    "pause_buffer_count": 0
  }
}
```

`reason` and `ssh_stderr_first_line` are populated only on
`state = "lost"` (FR-006 surfacing). `pause_buffer_count` is non-zero only
while `paused = true` and reflects the number of frames decoded but not
yet sent.

### `signal_update`

Batched. Each envelope carries up to ~200 changed signals; the server
coalesces multiple frames within a 100 ms window into one envelope to keep
WebSocket message rate ≤ 10 / s under steady-state load (matches SC-002's
200 ms p95 budget with headroom).

```json
{
  "kind": "signal_update",
  "payload": {
    "at_ms": 1714567890123,
    "signals": [
      {
        "name": "TS_BrakePedalPosition",
        "value": 0.42,
        "unit": "1",
        "channel": "A",
        "can_id": 256,
        "at_ms": 1714567890121
      },
      ...
    ]
  }
}
```

### `errq_update`

Diff against the previous active set. Sent at most once per second per
channel; empty envelopes are NOT sent.

```json
{
  "kind": "errq_update",
  "payload": {
    "appeared": [
      {
        "code": 4,
        "name": "TS_FOO_BAR_ERR",
        "description": "TS_FOO_BAR_ERR",
        "severity": "error",
        "channel": "A",
        "byte": 3,
        "bit": 2,
        "first_seen_ms": 1714567890123,
        "last_seen_ms": 1714567890123
      }
    ],
    "disappeared": [
      { "channel": "A", "byte": 5, "bit": 0 }
    ]
  }
}
```

### `raw_frame`

Sent only when `LiveFilter.raw_frames_enabled` is true. The server
rate-limits these to ≤ 1000 / s; on overflow, oldest are dropped per
FR-018.

```json
{
  "kind": "raw_frame",
  "payload": {
    "at_ms": 1714567890123,
    "can_id": 256,
    "dlc": 8,
    "payload_hex": "0102030405060708"
  }
}
```

### `error`

Recoverable backend errors that don't kill the session.

```json
{
  "kind": "error",
  "payload": {
    "code": "dbc_decode_failed | errq_model_unavailable | rate_limited",
    "message": "Could not decode CAN id 0x1FF — not in the loaded DBC."
  }
}
```

## Client → server messages

### `set_filter`

```json
{
  "kind": "set_filter",
  "payload": { "signal_name_substring": "BRAKE" }
}
```

Empty string clears the filter. Server replies with no immediate envelope
— the next `signal_update` reflects the new filter.

### `set_channel`

```json
{
  "kind": "set_channel",
  "payload": { "channel": "A | B | both" }
}
```

### `pause` / `resume` / `clear`

```json
{ "kind": "pause", "payload": {} }
```

```json
{ "kind": "resume", "payload": {} }
```

```json
{ "kind": "clear", "payload": {} }
```

`clear` MUST be confirmable client-side per US3 acceptance scenario 4 —
the SPA shows a confirm dialog before sending.

### `toggle_raw_frames`

```json
{
  "kind": "toggle_raw_frames",
  "payload": { "enabled": true }
}
```

## Close codes

| Code | Reason | Meaning |
|---|---|---|
| `1000` | (default) | Clean close — operator navigated away or clicked Close. |
| `1008` | `host_out_of_scope`, `unauthorized`, `developer_mode_off` | Policy violation — surfaced in the frontend as a redirect to main with a toast. |
| `1011` | `internal_error` | Unhandled backend exception. Log + report. |
| `4000` | `ssh_failed` | Custom code — SSH child exited before any frame was decoded. The server includes `ssh_stderr_first_line` in the most-recent `status` envelope so the frontend can render FR-006's plain-language error. |
| `4001` | `ssh_stalled` | No frames for ≥ 10 s. Triggers FR-017 reconnection banner. |

## Versioning

The contract is unversioned in v1. Future breaking changes either
(a) introduce a `protocol_version` field on the `ready` envelope and
support both versions for one release, or (b) move to
`/api/live/v2/{host_id}/ws`.

## Implementation notes

- The server MUST NOT log the operator's full `ssh` command line — the
  redacted form is `ssh <host> candump <iface>` (port + user override
  collapsed to "+overrides" if present). This avoids the small but
  non-zero risk of ProxyJump targets or unusual `~/.ssh/config` aliases
  leaking into logs.
- `signal_update` envelopes coalesce within a 100 ms window; the server
  keeps the most recent value per signal name + channel and emits the
  union once per window. This is what makes 1000 fps tractable.
- `errq_update` diffs are computed per channel; if both channels change
  in the same cycle, the envelope still includes both in `appeared` /
  `disappeared`.
