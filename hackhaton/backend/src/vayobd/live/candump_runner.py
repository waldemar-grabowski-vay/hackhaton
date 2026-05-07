"""SSH+candump async subprocess wrapper (T021).

Spawns the operator's local `ssh` binary to stream `candump` from a
testbed; emits parsed CAN frames on a queue.

Q2 of /speckit-clarify decided we shell out to the operator's local
`ssh` rather than using paramiko. That keeps SSH credentials,
ProxyJump, and `~/.ssh/config` exactly where they already are: on the
operator's machine. The implication: the FastAPI backend MUST run on
the operator's machine (localhost), not on a shared server.

Line format we parse — matches the desktop tool's regex:
    (1234567890.123) can0 100#0102030405060708          (classic CAN)
    (1234567890.123) can0 100##F0102030405060708...     (CAN FD)
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

log = logging.getLogger(__name__)

# Same patterns as TS_diagnostic_tool/ssh_can_reader.py.
_LINE_RE_FD = re.compile(
    r"^\((?P<ts>\d+\.\d+)\)\s+(?P<bus>\S+)\s+(?P<id>[0-9A-Fa-f]+)##"
    r"(?P<flags>[0-9A-Fa-f])(?P<data>[0-9A-Fa-f]*)\s*$"
)
_LINE_RE_CLASSIC = re.compile(
    r"^\((?P<ts>\d+\.\d+)\)\s+(?P<bus>\S+)\s+(?P<id>[0-9A-Fa-f]+)#"
    r"(?P<data>[0-9A-Fa-f]*)\s*$"
)


@dataclass(frozen=True)
class ParsedFrame:
    """One decoded candump line. `at_ms` is the server-side wall clock at
    parse time (ms since epoch) — the in-frame `ts` from candump is
    relative to bus start with `-tz`, which isn't useful as a wall
    clock. Sessions stamp envelopes with `at_ms`.
    """

    at_ms: int
    bus: str
    can_id: int
    ext: bool
    fd: bool
    dlc: int
    data: bytes
    raw_line: str


def parse_candump_line(line: str, at_ms: int) -> ParsedFrame | None:
    """Parse one `-tz -L`-formatted candump line. Returns None when the
    line doesn't match (e.g. stderr noise) so the caller can route it
    to a raw log instead.
    """
    line = line.strip()
    fd = False
    m = _LINE_RE_FD.match(line)
    if m:
        fd = True
    else:
        m = _LINE_RE_CLASSIC.match(line)
        if not m:
            return None

    raw_id = m.group("id")
    can_id = int(raw_id, 16)
    ext = len(raw_id) > 3
    data_hex = m.group("data") or ""
    if len(data_hex) % 2:
        data_hex = data_hex[:-1]
    data = bytes.fromhex(data_hex) if data_hex else b""
    return ParsedFrame(
        at_ms=at_ms,
        bus=m.group("bus"),
        can_id=can_id,
        ext=ext,
        fd=fd,
        dlc=len(data),
        data=data,
        raw_line=line,
    )


def _redacted_command(host: str, iface: str) -> str:
    """Per FR-021, log lines must not include user@/port/key arguments.

    Always log the redacted form `ssh <host> candump <iface>`, never
    the full argv.
    """
    return f"ssh {host} candump {iface}"


class CandumpRunner:
    """One ssh+candump subprocess. Streams parsed frames + raw lines.

    Lifecycle:
        runner = CandumpRunner(host_address="ts-de-ber-00005")
        await runner.start()
        async for frame_or_raw in runner.lines():
            ...
        await runner.terminate()
    """

    def __init__(
        self,
        host_address: str,
        iface: str = "can0",
        user: str | None = None,
        port: int | None = None,
    ) -> None:
        self.host_address = host_address
        self.iface = iface
        self.user = user
        self.port = port
        self._proc: asyncio.subprocess.Process | None = None
        self._target = (
            f"{user}@{host_address}" if user else host_address
        )

    @property
    def redacted_command(self) -> str:
        return _redacted_command(self.host_address, self.iface)

    async def start(self) -> None:
        """Spawn the ssh subprocess. Inherits the operator's
        `~/.ssh/config` and identity files transparently.
        """
        # Mirror desktop tool's CANDUMP_CMD_TEMPLATE.
        remote_cmd = f"stdbuf -oL -eL candump -tz -L {self.iface}"
        argv: list[str] = [
            "ssh",
            "-o", "BatchMode=yes",          # no interactive password prompts
            "-o", "ServerAliveInterval=10",  # detect stalls
            "-o", "ServerAliveCountMax=2",
            "-o", "ConnectTimeout=10",
        ]
        if self.port is not None:
            argv += ["-p", str(self.port)]
        argv += [self._target, remote_cmd]

        log.info("candump_starting", redacted=self.redacted_command)
        self._proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
        )

    @property
    def returncode(self) -> int | None:
        return self._proc.returncode if self._proc else None

    async def lines(self) -> AsyncIterator[tuple[str, str]]:
        """Yield `(stream, line)` tuples where `stream` is "out" or
        "err" — both stdout and stderr lines are surfaced so the
        caller can route stderr into the raw log / status messages.
        """
        if self._proc is None:
            raise RuntimeError("CandumpRunner.start() not called")

        async def _read_stream(stream, label: str, q: asyncio.Queue) -> None:
            while True:
                raw = await stream.readline()
                if not raw:
                    await q.put(None)  # EOF sentinel
                    return
                text = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if text:
                    await q.put((label, text))

        q: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue(maxsize=4096)
        out_task = asyncio.create_task(
            _read_stream(self._proc.stdout, "out", q),
            name="candump-stdout",
        )
        err_task = asyncio.create_task(
            _read_stream(self._proc.stderr, "err", q),
            name="candump-stderr",
        )

        eofs = 0
        try:
            while eofs < 2:
                item = await q.get()
                if item is None:
                    eofs += 1
                    continue
                yield item
        finally:
            for t in (out_task, err_task):
                if not t.done():
                    t.cancel()

    async def stderr_first_line(self, timeout: float = 0.5) -> str | None:
        """Helper for FR-006: peek at stderr without blocking forever.
        Returns `None` if nothing arrived within `timeout`.
        """
        if self._proc is None or self._proc.stderr is None:
            return None
        try:
            line = await asyncio.wait_for(
                self._proc.stderr.readline(), timeout=timeout
            )
        except TimeoutError:
            return None
        return line.decode("utf-8", errors="replace").rstrip("\r\n") or None

    async def terminate(self, grace: float = 2.0) -> None:
        """SIGTERM, wait `grace` seconds, then SIGKILL."""
        if self._proc is None:
            return
        if self._proc.returncode is not None:
            return
        try:
            self._proc.terminate()
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(self._proc.wait(), timeout=grace)
        except TimeoutError:
            log.warning("candump_grace_expired", redacted=self.redacted_command)
            try:
                self._proc.kill()
            except ProcessLookupError:
                pass
            await self._proc.wait()
        log.info(
            "candump_stopped",
            redacted=self.redacted_command,
            exit=self._proc.returncode,
        )


def now_ms() -> int:
    return int(time.time() * 1000)
