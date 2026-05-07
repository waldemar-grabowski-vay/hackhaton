"""WebSocket envelope models for `/api/live/{host_id}/ws` (T011).

Mirrors `specs/004-ts-diag-browser/contracts/websocket.md`. Both sides
validate (Pydantic here, Zod on the frontend); unknown `kind` values are
silently dropped (forward-compat).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---- domain types (mirrored on the frontend as well) ----------------------


class DecodedSignal(BaseModel):
    name: str
    value: float | bool | int | str | None
    unit: str | None = None
    channel: Literal["A", "B", "unknown"]
    can_id: int
    at_ms: int


class ErrqEntryEnvelope(BaseModel):
    """Wire form of `errq_state.ErrqEntry`. Note `bit` is the 0-based
    bit index (decoded from `bit_mask`); we keep `code` for the raw
    bit value for compatibility with the desktop tool's display.
    """

    code: int
    name: str | None
    description: str
    severity: Literal["info", "warn", "error", "critical"] | None
    channel: Literal["A", "B"]
    byte: int
    bit: int
    first_seen_ms: int
    last_seen_ms: int


class ErrqDisappearedKey(BaseModel):
    channel: Literal["A", "B"]
    byte: int
    bit: int


class RawFrame(BaseModel):
    at_ms: int
    can_id: int
    dlc: int
    payload_hex: str


# ---- server -> client envelopes ------------------------------------------


class ReadyPayload(BaseModel):
    session_id: str
    host_id: str
    errq_loaded: bool
    errq_source_path: str | None
    dbc_loaded: bool
    dbc_source_path: str | None
    server_build: str | None


class StatusPayload(BaseModel):
    state: Literal["connecting", "connected", "lost", "closed"]
    reason: str | None = None
    ssh_stderr_first_line: str | None = None
    since_ms: int
    pause_buffer_count: int = 0


class SignalUpdatePayload(BaseModel):
    at_ms: int
    signals: list[DecodedSignal]


class ErrqUpdatePayload(BaseModel):
    appeared: list[ErrqEntryEnvelope] = Field(default_factory=list)
    disappeared: list[ErrqDisappearedKey] = Field(default_factory=list)


class RawFramePayload(RawFrame):
    pass


class ErrorPayload(BaseModel):
    code: Literal["dbc_decode_failed", "errq_model_unavailable", "rate_limited"]
    message: str


class ReadyEnvelope(BaseModel):
    kind: Literal["ready"] = "ready"
    payload: ReadyPayload


class StatusEnvelope(BaseModel):
    kind: Literal["status"] = "status"
    payload: StatusPayload


class SignalUpdateEnvelope(BaseModel):
    kind: Literal["signal_update"] = "signal_update"
    payload: SignalUpdatePayload


class ErrqUpdateEnvelope(BaseModel):
    kind: Literal["errq_update"] = "errq_update"
    payload: ErrqUpdatePayload


class RawFrameEnvelope(BaseModel):
    kind: Literal["raw_frame"] = "raw_frame"
    payload: RawFramePayload


class ErrorEnvelope(BaseModel):
    kind: Literal["error"] = "error"
    payload: ErrorPayload


ServerEnvelope = Annotated[
    ReadyEnvelope
    | StatusEnvelope
    | SignalUpdateEnvelope
    | ErrqUpdateEnvelope
    | RawFrameEnvelope
    | ErrorEnvelope,
    Field(discriminator="kind"),
]


# ---- client -> server envelopes ------------------------------------------


class SetFilterPayload(BaseModel):
    signal_name_substring: str = ""


class SetChannelPayload(BaseModel):
    channel: Literal["A", "B", "both"]


class TogglePayload(BaseModel):
    enabled: bool


class _Empty(BaseModel):
    model_config = ConfigDict(extra="ignore")


class SetFilterEnvelope(BaseModel):
    kind: Literal["set_filter"] = "set_filter"
    payload: SetFilterPayload


class SetChannelEnvelope(BaseModel):
    kind: Literal["set_channel"] = "set_channel"
    payload: SetChannelPayload


class PauseEnvelope(BaseModel):
    kind: Literal["pause"] = "pause"
    payload: _Empty = Field(default_factory=_Empty)


class ResumeEnvelope(BaseModel):
    kind: Literal["resume"] = "resume"
    payload: _Empty = Field(default_factory=_Empty)


class ClearEnvelope(BaseModel):
    kind: Literal["clear"] = "clear"
    payload: _Empty = Field(default_factory=_Empty)


class ToggleRawFramesEnvelope(BaseModel):
    kind: Literal["toggle_raw_frames"] = "toggle_raw_frames"
    payload: TogglePayload


ClientEnvelope = Annotated[
    SetFilterEnvelope
    | SetChannelEnvelope
    | PauseEnvelope
    | ResumeEnvelope
    | ClearEnvelope
    | ToggleRawFramesEnvelope,
    Field(discriminator="kind"),
]
