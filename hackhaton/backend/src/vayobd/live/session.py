"""LiveDiagnosticSession state machine (T022).

Per WebSocket. Owns a `CandumpRunner`, the per-session `ErrqAggregator`
+ `ErrqStateTracker`, and a bounded outbound queue. Emits envelopes per
`contracts/websocket.md`:

  ready → status:connecting → (status:connected after first frame) →
  signal_update + errq_update + raw_frame (when toggled) →
  status:lost on stall or ssh exit → close

The pipeline is split into three asyncio tasks:
  1. `_drain_lines` — pulls `(stream, line)` from the runner, decodes
     CAN frames, feeds the aggregator + state tracker, accumulates a
     coalesced `signal_update` payload, watches the 10 s heartbeat.
  2. `_emit_loop` — every 100 ms, flushes the coalesced payload as one
     `signal_update` envelope; checks errq diffs and emits
     `errq_update`; pushes everything onto the outbound queue.
  3. `_ws_loop` — reads inbound JSON from the WebSocket, validates as
     `ClientEnvelope`, mutates session state.

The orchestrator in `run()` waits on all three with `asyncio.wait` and
tears the rest down whenever the first one finishes.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Literal

from fastapi import WebSocket
from pydantic import ValidationError

from vayobd.live.candump_runner import CandumpRunner, now_ms, parse_candump_line
from vayobd.live.dbc_decoder import DbcDecoder
from vayobd.live.errq_aggregator import ErrqAggregator
from vayobd.live.errq_loader import ErrqModel
from vayobd.live.errq_state import ErrqEntry, ErrqStateTracker
from vayobd.live.live_models import (
    ClientEnvelope,
    DecodedSignal,
    ErrqDisappearedKey,
    ErrqEntryEnvelope,
    ErrqUpdateEnvelope,
    ErrqUpdatePayload,
    RawFrameEnvelope,
    RawFramePayload,
    ReadyEnvelope,
    ReadyPayload,
    SignalUpdateEnvelope,
    SignalUpdatePayload,
    StatusEnvelope,
    StatusPayload,
)

log = logging.getLogger(__name__)

# Tuning constants.
COALESCE_INTERVAL_MS = 100        # window for batching signal_update envelopes
HEARTBEAT_TIMEOUT_S = 10.0        # FR-017 stall detection
OUTBOUND_QUEUE_MAX = 512          # FR-018 newest-wins overflow
RAW_FRAMES_RATE_LIMIT = 1000      # contracts/websocket.md, raw_frame
SIGNAL_UPDATE_MAX_BATCH = 500     # cap envelope size at runaway rate

# FR-026 — channel inference defaults. Used when (a) settings provide
# no patterns or (b) operator-supplied patterns fail to compile.
DEFAULT_CHANNEL_A_PATTERN = r"(?i)_CHA_|TS_CHA"
DEFAULT_CHANNEL_B_PATTERN = r"(?i)_CHB_|TS_CHB"


def _compile_channel_pattern(pattern: str, channel: str) -> re.Pattern[str]:
    """Compile an operator-supplied channel-inference regex. On invalid
    regex, log a warning and fall back to the default for that channel
    rather than crashing the session (FR-026: surfaces are still
    operable when operators typo a pattern).
    """
    try:
        return re.compile(pattern)
    except re.error as exc:
        default = (
            DEFAULT_CHANNEL_A_PATTERN if channel == "A" else DEFAULT_CHANNEL_B_PATTERN
        )
        log.warning(
            "channel_pattern_invalid: channel=%s pattern=%r error=%s falling_back_to=%r",
            channel,
            pattern,
            str(exc),
            default,
        )
        return re.compile(default)

# WebSocket close codes (contracts/websocket.md §"Close codes").
CLOSE_OK = 1000
CLOSE_POLICY = 1008
CLOSE_INTERNAL = 1011
CLOSE_SSH_FAILED = 4000
CLOSE_SSH_STALLED = 4001


@dataclass
class LiveFilter:
    channel: Literal["A", "B", "both"] = "both"
    signal_name_substring: str = ""
    raw_frames_enabled: bool = False


@dataclass
class _CoalesceBuffer:
    """Newest-wins buffer of signals seen in the current 100 ms window.
    Keyed by `(name, channel)`. Drained on emit.
    """

    items: dict[tuple[str, str], DecodedSignal] = field(default_factory=dict)

    def merge(self, sig: DecodedSignal) -> None:
        self.items[(sig.name, sig.channel)] = sig

    def drain(self) -> list[DecodedSignal]:
        out = list(self.items.values())
        self.items.clear()
        return out


class LiveDiagnosticSession:
    def __init__(
        self,
        websocket: WebSocket,
        host_id: str,
        host_address: str,
        operator_slug: str,
        errq_model: ErrqModel | None,
        dbc_decoder: DbcDecoder | None,
        server_build: str | None,
        user_override: str | None = None,
        port_override: int | None = None,
        iface: str = "can0",
        channel_a_pattern: str = DEFAULT_CHANNEL_A_PATTERN,
        channel_b_pattern: str = DEFAULT_CHANNEL_B_PATTERN,
    ) -> None:
        self.ws = websocket
        self.host_id = host_id
        self.host_address = host_address
        self.operator_slug = operator_slug
        self.errq_model = errq_model
        self.dbc_decoder = dbc_decoder
        self.server_build = server_build
        self.session_id = str(uuid.uuid4())
        self.started_at_ms = now_ms()

        self.runner = CandumpRunner(
            host_address=host_address,
            iface=iface,
            user=user_override,
            port=port_override,
        )

        self.aggregator = ErrqAggregator()
        self.state_tracker = ErrqStateTracker()

        # FR-026 — compile regexes once; fall back to defaults on
        # invalid patterns so the session still serves traffic.
        self._channel_a_re = _compile_channel_pattern(channel_a_pattern, "A")
        self._channel_b_re = _compile_channel_pattern(channel_b_pattern, "B")

        self.filter = LiveFilter()
        self.paused = False
        self.pause_buffer_count = 0

        self.coalesce = _CoalesceBuffer()
        self.outbound: asyncio.Queue[dict] = asyncio.Queue(maxsize=OUTBOUND_QUEUE_MAX)

        self._first_frame_seen = False
        self._last_frame_at_s = time.monotonic()
        self._last_raw_frame_burst_start_s = 0.0
        self._raw_frame_burst_count = 0
        self._stderr_first_line: str | None = None

        self._close_code: int | None = None
        self._close_reason: str = ""

    # ---- envelope helpers --------------------------------------------------

    def _enqueue(self, payload: dict) -> None:
        """FR-018: newest-wins. If the queue is full, drop the oldest."""
        try:
            self.outbound.put_nowait(payload)
        except asyncio.QueueFull:
            try:
                self.outbound.get_nowait()
                self.outbound.put_nowait(payload)
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass

    def _status(
        self,
        state: Literal["connecting", "connected", "lost", "closed"],
        reason: str | None = None,
        ssh_stderr_first_line: str | None = None,
    ) -> dict:
        env = StatusEnvelope(
            payload=StatusPayload(
                state=state,
                reason=reason,
                ssh_stderr_first_line=ssh_stderr_first_line,
                since_ms=now_ms(),
                pause_buffer_count=self.pause_buffer_count,
            )
        )
        return env.model_dump()

    # ---- pipeline tasks ----------------------------------------------------

    async def _drain_lines(self) -> None:
        """Read every line from the candump runner; decode + aggregate."""
        async for stream, raw in self.runner.lines():
            if stream != "out":
                if self._stderr_first_line is None:
                    self._stderr_first_line = raw[:200]
                log.debug("candump_stderr", line=raw[:200])
                continue
            self._handle_frame_line(raw)

    def _handle_frame_line(self, raw: str) -> None:
        frame = parse_candump_line(raw, now_ms())
        if frame is None:
            return

        # First-frame handshake: flip status to "connected".
        if not self._first_frame_seen:
            self._first_frame_seen = True
            self._enqueue(self._status("connected"))
        self._last_frame_at_s = time.monotonic()

        # Optional raw-frame surfacing (rate-limited).
        if self.filter.raw_frames_enabled:
            self._maybe_enqueue_raw(frame)

        # DBC decode + signal extraction.
        decoded = (
            self.dbc_decoder.decode(
                at_ms=frame.at_ms,
                bus=frame.bus,
                can_id=frame.can_id,
                ext=frame.ext,
                data=frame.data,
            )
            if self.dbc_decoder and self.dbc_decoder.loaded
            else None
        )
        if decoded is None or not decoded.signals:
            return

        # Feed the errq aggregator with the freshly decoded signals.
        touched = self.aggregator.ingest(decoded.signals)
        for ch in touched:
            buf = self.aggregator.snapshot(ch)
            self.state_tracker.update_buffer(
                channel=ch,
                buffer=buf,
                ts=frame.at_ms / 1000.0,
                bus=frame.bus,
                can_id=frame.can_id,
                hex_id=f"{frame.can_id:X}",
                decode_buffer_fn=(
                    self.errq_model.decode_buffer
                    if self.errq_model and self.errq_model.loaded
                    else (lambda *_: [])
                ),
            )

        # Coalesce decoded signals into the next signal_update envelope.
        for name, value in decoded.signals.items():
            channel = self._infer_channel(name)
            if not self._passes_filter(name, channel):
                continue
            sig = DecodedSignal(
                name=name,
                value=_safe_value(value),
                unit=None,  # cantools' decoder doesn't surface units inline; future enhancement
                channel=channel,
                can_id=frame.can_id,
                at_ms=frame.at_ms,
            )
            self.coalesce.merge(sig)

    def _passes_filter(self, name: str, channel: Literal["A", "B", "unknown"]) -> bool:
        if (
            self.filter.channel != "both"
            and channel != "unknown"
            and channel != self.filter.channel
        ):
            return False
        sub = self.filter.signal_name_substring.strip()
        if sub and sub.lower() not in name.lower():
            return False
        return True

    def _infer_channel(self, name: str) -> Literal["A", "B", "unknown"]:
        """Classify a signal into Channel A / B / unknown using the
        per-session compiled regexes. First match wins; signals
        matching neither pattern fall through to `unknown`. FR-026.
        """
        if self._channel_a_re.search(name):
            return "A"
        if self._channel_b_re.search(name):
            return "B"
        return "unknown"

    def _maybe_enqueue_raw(self, frame) -> None:
        # Token-bucket: cap at RAW_FRAMES_RATE_LIMIT per second.
        now_s = time.monotonic()
        if now_s - self._last_raw_frame_burst_start_s >= 1.0:
            self._last_raw_frame_burst_start_s = now_s
            self._raw_frame_burst_count = 0
        if self._raw_frame_burst_count >= RAW_FRAMES_RATE_LIMIT:
            return
        self._raw_frame_burst_count += 1
        env = RawFrameEnvelope(
            payload=RawFramePayload(
                at_ms=frame.at_ms,
                can_id=frame.can_id,
                dlc=frame.dlc,
                payload_hex=frame.data.hex(),
            )
        )
        self._enqueue(env.model_dump())

    async def _emit_loop(self) -> None:
        """Every 100 ms: flush coalesced signals + emit errq diff."""
        # Track which (channel, byte, bit) keys we've reported as
        # appeared so we can compute disappear diffs locally.
        active_keys: set[tuple[str, int, int]] = set()

        while True:
            await asyncio.sleep(COALESCE_INTERVAL_MS / 1000.0)

            # 10 s no-frame stall detection.
            if (
                self._first_frame_seen
                and time.monotonic() - self._last_frame_at_s > HEARTBEAT_TIMEOUT_S
            ):
                self._close_code = CLOSE_SSH_STALLED
                self._close_reason = "ssh_stalled"
                self._enqueue(
                    self._status("lost", reason="ssh_stalled", ssh_stderr_first_line=self._stderr_first_line)
                )
                return

            active_keys = self._emit_one_cycle(active_keys)

    def _emit_one_cycle(
        self, active_keys: set[tuple[str, int, int]]
    ) -> set[tuple[str, int, int]]:
        """One iteration of the emit pipeline: flush coalesced
        signals then compute + enqueue the errq diff. Extracted from
        `_emit_loop` so tests can drive a single cycle without the
        100 ms `asyncio.sleep`.

        Returns the new `active_keys` set for the next cycle.
        """
        # Flush signals.
        if not self.paused:
            signals = self.coalesce.drain()
            if signals:
                if len(signals) > SIGNAL_UPDATE_MAX_BATCH:
                    signals = signals[:SIGNAL_UPDATE_MAX_BATCH]
                env = SignalUpdateEnvelope(
                    payload=SignalUpdatePayload(at_ms=now_ms(), signals=signals)
                )
                self._enqueue(env.model_dump())
        else:
            # While paused: count how many signals we'd have sent.
            self.pause_buffer_count = len(self.coalesce.items)

        # Errq diff.
        current = self._collect_active_errq()
        current_keys = {(e.channel, e.byte, e.bit) for e in current}
        appeared_keys = current_keys - active_keys
        disappeared_keys = active_keys - current_keys

        if appeared_keys or disappeared_keys:
            appeared = [e for e in current if (e.channel, e.byte, e.bit) in appeared_keys]
            env = ErrqUpdateEnvelope(
                payload=ErrqUpdatePayload(
                    appeared=appeared,
                    disappeared=[
                        ErrqDisappearedKey(channel=k[0], byte=k[1], bit=k[2])  # type: ignore[arg-type]
                        for k in disappeared_keys
                    ],
                )
            )
            self._enqueue(env.model_dump())

        return current_keys

    def _collect_active_errq(self) -> list[ErrqEntryEnvelope]:
        out: list[ErrqEntryEnvelope] = []
        for entry in self.state_tracker.values():
            if entry.status != "active":
                continue
            if self.filter.channel != "both" and entry.channel != self.filter.channel:
                continue
            out.append(_to_errq_envelope(entry))
        return out

    async def _ws_loop(self) -> None:
        """Drain inbound client envelopes."""
        while True:
            try:
                raw = await self.ws.receive_text()
            except Exception:  # WebSocketDisconnect or transport error
                self._close_code = CLOSE_OK
                self._close_reason = "client_disconnected"
                return
            try:
                obj = json.loads(raw)
                env = _validate_client_envelope(obj)
            except (json.JSONDecodeError, ValidationError) as exc:
                log.debug("ws_invalid_envelope", error=str(exc))
                continue
            self._apply_client(env)

    def _apply_client(self, env: ClientEnvelope) -> None:
        kind = env.kind
        if kind == "set_filter":
            self.filter.signal_name_substring = env.payload.signal_name_substring
        elif kind == "set_channel":
            self.filter.channel = env.payload.channel
        elif kind == "pause":
            self.paused = True
        elif kind == "resume":
            self.paused = False
            # Flush the buffered snapshot once on resume.
            signals = self.coalesce.drain()
            if signals:
                env_out = SignalUpdateEnvelope(
                    payload=SignalUpdatePayload(at_ms=now_ms(), signals=signals)
                )
                self._enqueue(env_out.model_dump())
            self.pause_buffer_count = 0
        elif kind == "clear":
            self.coalesce.items.clear()
            self.aggregator.reset()
            self.state_tracker.reset()
        elif kind == "toggle_raw_frames":
            self.filter.raw_frames_enabled = env.payload.enabled

    async def _outbound_loop(self) -> None:
        """Drain the outbound queue → WebSocket."""
        while True:
            payload = await self.outbound.get()
            try:
                await self.ws.send_json(payload)
            except Exception:
                self._close_code = CLOSE_OK
                self._close_reason = "client_disconnected"
                return

    # ---- orchestrator ------------------------------------------------------

    async def run(self) -> None:
        """Send `ready` + `status:connecting`, spawn ssh, run pipeline,
        send `status:lost` (or whatever applies) when one of the
        coroutines finishes, then close the WebSocket.
        """
        await self.ws.send_json(
            ReadyEnvelope(
                payload=ReadyPayload(
                    session_id=self.session_id,
                    host_id=self.host_id,
                    errq_loaded=bool(self.errq_model and self.errq_model.loaded),
                    errq_source_path=str(self.errq_model.source_path) if self.errq_model else None,
                    dbc_loaded=bool(self.dbc_decoder and self.dbc_decoder.loaded),
                    dbc_source_path=str(self.dbc_decoder.dbc_path)
                    if self.dbc_decoder and self.dbc_decoder.dbc_path
                    else None,
                    server_build=self.server_build,
                )
            ).model_dump()
        )
        await self.ws.send_json(self._status("connecting"))

        try:
            await self.runner.start()
        except FileNotFoundError as exc:
            await self.ws.send_json(
                self._status(
                    "lost",
                    reason="ssh_not_found",
                    ssh_stderr_first_line=str(exc),
                )
            )
            await self._close(CLOSE_SSH_FAILED, "ssh_not_found")
            return
        except OSError as exc:
            await self.ws.send_json(
                self._status(
                    "lost",
                    reason="spawn_failed",
                    ssh_stderr_first_line=str(exc),
                )
            )
            await self._close(CLOSE_SSH_FAILED, "spawn_failed")
            return

        tasks = [
            asyncio.create_task(self._drain_lines(), name=f"live-{self.session_id}-drain"),
            asyncio.create_task(self._emit_loop(), name=f"live-{self.session_id}-emit"),
            asyncio.create_task(self._ws_loop(), name=f"live-{self.session_id}-ws"),
            asyncio.create_task(self._outbound_loop(), name=f"live-{self.session_id}-out"),
        ]
        try:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
            for t in pending:
                with suppress(asyncio.CancelledError, Exception):
                    await t

            # Did the candump child exit before any frame arrived?
            rc = self.runner.returncode
            if rc is not None and rc != 0 and not self._first_frame_seen:
                self._close_code = CLOSE_SSH_FAILED
                self._close_reason = "ssh_failed"
                stderr = self._stderr_first_line or f"ssh exited with code {rc}"
                with suppress(Exception):
                    await self.ws.send_json(
                        self._status("lost", reason="ssh_failed", ssh_stderr_first_line=stderr)
                    )
        finally:
            await self.runner.terminate()
            await self._close(self._close_code or CLOSE_OK, self._close_reason or "ok")

    async def _close(self, code: int, reason: str) -> None:
        with suppress(Exception):
            await self.ws.close(code=code, reason=reason[:120])
        log.info(
            "live_session_closed",
            session_id=self.session_id,
            host_id=self.host_id,
            code=code,
            reason=reason,
        )


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _to_errq_envelope(entry: ErrqEntry) -> ErrqEntryEnvelope:
    bit_index = entry.bit_mask.bit_length() - 1 if entry.bit_mask else 0
    return ErrqEntryEnvelope(
        code=entry.bit_mask,
        name=entry.name,
        description=entry.description,
        severity=entry.severity,  # type: ignore[arg-type]
        channel=entry.channel,    # type: ignore[arg-type]
        byte=entry.byte,
        bit=bit_index,
        first_seen_ms=int(entry.first_seen * 1000),
        last_seen_ms=int(entry.last_active * 1000),
    )


def _validate_client_envelope(obj: object) -> ClientEnvelope:
    """Pydantic discriminated-union validation. Raises ValidationError on
    mismatch — caller catches and logs.
    """
    from pydantic import TypeAdapter

    adapter = TypeAdapter(ClientEnvelope)
    return adapter.validate_python(obj)


def _safe_value(value: object) -> float | bool | int | str | None:
    """Coerce cantools' decoded value into something JSON-serialisable."""
    if value is None:
        return None
    if isinstance(value, (int, float, bool, str)):
        return value
    # NamedSignalValue (cantools choice) has a __str__ that returns the
    # symbolic name and a `value` int attribute. Prefer the symbolic name.
    name = getattr(value, "name", None)
    if isinstance(name, str):
        return name
    return str(value)
