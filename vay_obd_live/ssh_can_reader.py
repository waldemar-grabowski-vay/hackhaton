"""
SSH + candump live streamer.

Opens an SSH session to the remote host, discovers every UP can* interface,
and runs one `candump` per bus on its own channel. Lines are parsed and
pushed onto a thread-safe queue for the UI to drain.

Auth strategy (tried in order, first success wins):
    1. Explicit `key_filename` argument
    2. Each existing file in SSH_KEY_CANDIDATES (incl. WSL home fallback)
    3. The local SSH agent + default key locations
    4. Password, if supplied

Frame format pushed to the queue:
    {
        "ts":     float,        # seconds, absolute (host clock from -tz)
        "bus":    str,          # "can0", "can1", ...
        "can_id": int,          # arbitration id (extended bit handled)
        "ext":    bool,         # True if 29-bit
        "dlc":    int,
        "data":   bytes,
    }
"""
from __future__ import annotations

import logging
import os
import queue
import re
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import paramiko

from config import (
    CAN_DETECT_CMD,
    CANDUMP_CMD_TEMPLATE,
    FORWARD_AGENT,
    REMOTE_HOST,
    REMOTE_PORT,
    REMOTE_USER,
    SSH_KEY_CANDIDATES,
    WSL_DISTRO,
)

log = logging.getLogger(__name__)


# ----- candump -L line parser --------------------------------------------
# candump emits two frame styles in -L log format:
#
#   Classic CAN:   (ts) iface id#data
#                  e.g. (1700000000.123) can0 18FF50E5#0102030405060708
#
#   CAN FD:        (ts) iface id##F<data>   (F = single-hex flags nibble)
#                  e.g. (51.253936) can0 004##5050000000040008106030AC51C8...
#
# We try the FD pattern first because its `##` is a strict superset prefix
# of the classic `#`; classic regex would fail on FD lines anyway because
# the next char after `#` would be another `#`, not hex.
_LINE_RE_FD = re.compile(
    r"^\((?P<ts>\d+\.\d+)\)\s+(?P<bus>\S+)\s+(?P<id>[0-9A-Fa-f]+)##"
    r"(?P<flags>[0-9A-Fa-f])(?P<data>[0-9A-Fa-f]*)\s*$"
)
_LINE_RE_CLASSIC = re.compile(
    r"^\((?P<ts>\d+\.\d+)\)\s+(?P<bus>\S+)\s+(?P<id>[0-9A-Fa-f]+)#"
    r"(?P<data>[0-9A-Fa-f]*)\s*$"
)


def _detect_wsl_home(distro: str | None = None, user: str | None = None) -> Path | None:
    """
    Return a Path to \\wsl$\<distro>\home\<user> if it exists, else None.

    On non-Windows platforms this returns None and the caller skips the
    WSL fallback entirely.
    """
    if os.name != "nt":
        return None
    user = user or os.environ.get("USER") or os.environ.get("USERNAME") or ""
    if not user:
        return None
    base = Path(r"\\wsl$")
    candidates: list[Path] = []
    if distro:
        candidates.append(base / distro / "home" / user)
    else:
        try:
            for entry in base.iterdir():
                candidates.append(entry / "home" / user)
        except OSError:
            return None
    for c in candidates:
        try:
            if c.exists():
                return c
        except OSError:
            continue
    return None


def resolve_key_candidates(
    patterns: Iterable[str] = SSH_KEY_CANDIDATES,
    distro: str | None = WSL_DISTRO,
) -> list[Path]:
    """Expand {USERPROFILE} / {WSL_HOME} placeholders and keep the existing files."""
    userprofile = os.environ.get("USERPROFILE") or str(Path.home())
    wsl_home = _detect_wsl_home(distro)
    out: list[Path] = []
    for pat in patterns:
        if "{WSL_HOME}" in pat:
            if not wsl_home:
                continue
            pat = pat.replace("{WSL_HOME}", str(wsl_home))
        if "{USERPROFILE}" in pat:
            pat = pat.replace("{USERPROFILE}", userprofile)
        p = Path(os.path.expandvars(pat)).expanduser()
        try:
            if p.is_file():
                out.append(p)
        except OSError:
            continue
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in out:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def parse_candump_line(line: str) -> dict | None:
    line = line.strip()
    fd = False
    flags = 0
    m = _LINE_RE_FD.match(line)
    if m:
        fd = True
        flags = int(m.group("flags"), 16)
    else:
        m = _LINE_RE_CLASSIC.match(line)
        if not m:
            return None

    raw_id = m.group("id")
    can_id = int(raw_id, 16)
    ext = len(raw_id) > 3
    data_hex = m.group("data") or ""
    # candump emits an even number of hex chars for the payload; if for
    # some reason it's odd, drop the dangling nibble rather than raising.
    if len(data_hex) % 2:
        data_hex = data_hex[:-1]
    data = bytes.fromhex(data_hex) if data_hex else b""
    return {
        "ts": float(m.group("ts")),
        "bus": m.group("bus"),
        "can_id": can_id,
        "ext": ext,
        "fd": fd,
        "flags": flags,
        "dlc": len(data),
        "data": data,
    }


# ----- streamer -----------------------------------------------------------
@dataclass
class BusReader:
    iface: str
    channel: paramiko.Channel
    thread: threading.Thread


class CanStreamer:
    """
    Owns the paramiko connection and one BusReader per UP can interface.
    """

    def __init__(
        self,
        on_frame: Callable[[dict], None] | None = None,
        on_status: Callable[[str], None] | None = None,
        host: str = REMOTE_HOST,
        user: str = REMOTE_USER,
        port: int = REMOTE_PORT,
    ):
        self._host = host
        self._user = user
        self._port = port
        self._client: paramiko.SSHClient | None = None
        self._readers: list[BusReader] = []
        self._stop = threading.Event()
        self.frame_queue: queue.Queue[dict] = queue.Queue(maxsize=10000)
        # Raw text lines from candump (stdout + stderr), pushed line-by-line
        # so the UI can show them even when they don't match the parser.
        # Items: {"bus": str, "text": str, "stream": "out"|"err"}
        self.raw_queue: queue.Queue[dict] = queue.Queue(maxsize=20000)
        self._on_frame = on_frame
        self._on_status = on_status or (lambda s: log.info(s))

    # ---- connection ----
    def connect(
        self,
        host: str | None = None,
        user: str | None = None,
        port: int | None = None,
        key_filename: str | Path | None = None,
        passphrase: str | None = None,
        password: str | None = None,
    ) -> None:
        if host is not None:
            self._host = host
        if user is not None:
            self._user = user
        if port is not None:
            self._port = port

        self._on_status(f"Connecting to {self._user}@{self._host}:{self._port} ...")

        key_files: list[Path] = []
        if key_filename:
            kp = Path(str(key_filename)).expanduser()
            if kp.is_file():
                key_files.append(kp)
            else:
                raise FileNotFoundError(f"Key file not found: {kp}")
        key_files.extend(resolve_key_candidates())

        last_exc: Exception | None = None
        client: paramiko.SSHClient | None = None

        # Attempt 1..N: explicit key files
        for kf in key_files:
            client = self._new_client()
            try:
                self._on_status(f"Trying key {kf} ...")
                client.connect(
                    hostname=self._host,
                    port=self._port,
                    username=self._user,
                    key_filename=str(kf),
                    passphrase=passphrase,
                    allow_agent=False,
                    look_for_keys=False,
                    timeout=10,
                    banner_timeout=10,
                    auth_timeout=10,
                )
                self._on_status(f"Authenticated with {kf.name}.")
                break
            except paramiko.AuthenticationException as exc:
                last_exc = exc
                client.close()
                client = None
                continue
            except (paramiko.SSHException, socket.error):
                if client:
                    client.close()
                raise

        # Attempt N+1: SSH agent + default key locations
        if client is None:
            client = self._new_client()
            try:
                self._on_status("Trying SSH agent / default key locations ...")
                client.connect(
                    hostname=self._host,
                    port=self._port,
                    username=self._user,
                    allow_agent=True,
                    look_for_keys=True,
                    timeout=10,
                    banner_timeout=10,
                    auth_timeout=10,
                )
                self._on_status("Authenticated via agent / default key.")
            except paramiko.AuthenticationException as exc:
                last_exc = exc
                client.close()
                client = None

        # Attempt last: password
        if client is None and password:
            client = self._new_client()
            try:
                self._on_status("Trying password authentication ...")
                client.connect(
                    hostname=self._host,
                    port=self._port,
                    username=self._user,
                    password=password,
                    allow_agent=False,
                    look_for_keys=False,
                    timeout=10,
                    banner_timeout=10,
                    auth_timeout=10,
                )
                self._on_status("Authenticated with password.")
            except paramiko.AuthenticationException as exc:
                last_exc = exc
                client.close()
                client = None

        if client is None:
            raise last_exc or paramiko.AuthenticationException(
                "All authentication methods failed"
            )

        if FORWARD_AGENT:
            try:
                session = client.get_transport().open_session()
                paramiko.agent.AgentRequestHandler(session)
                session.close()
            except Exception as exc:  # noqa: BLE001
                log.warning("Agent forwarding failed: %s", exc)

        self._client = client
        self._on_status("SSH connected.")

    @staticmethod
    def _new_client() -> paramiko.SSHClient:
        c = paramiko.SSHClient()
        c.load_system_host_keys()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        return c

    # ---- discovery ----
    def discover_buses(self) -> list[str]:
        if not self._client:
            raise RuntimeError("SSH not connected")
        stdin, stdout, stderr = self._client.exec_command(CAN_DETECT_CMD, timeout=5)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        if err.strip():
            log.warning("can detect stderr: %s", err.strip())
        ifaces: list[str] = []
        for line in out.splitlines():
            parts = line.split()
            if not parts:
                continue
            name = parts[0]
            state = parts[1] if len(parts) > 1 else ""
            if name.startswith("can") and state.upper() in {"UP", "UNKNOWN"}:
                ifaces.append(name)
        if not ifaces:
            self._on_status(
                "No CAN interfaces auto-detected as UP — falling back to can0,can1."
            )
            ifaces = ["can0", "can1"]
        else:
            self._on_status(f"Detected CAN interfaces: {', '.join(ifaces)}")
        return ifaces

    # ---- start / stop ----
    def start(self, ifaces: Iterable[str]) -> None:
        if not self._client:
            raise RuntimeError("SSH not connected")
        self._stop.clear()
        for iface in ifaces:
            self._spawn_reader(iface)

    def _spawn_reader(self, iface: str) -> None:
        assert self._client is not None
        cmd = CANDUMP_CMD_TEMPLATE.format(iface=iface)
        transport = self._client.get_transport()
        chan = transport.open_session()
        # Deliberately NOT requesting a PTY: paramiko's PTY mangles line
        # endings and forces stderr onto stdout. With a plain exec we can
        # read stdout and stderr separately, and the `stdbuf -oL -eL`
        # prefix in CANDUMP_CMD_TEMPLATE handles line buffering for us.
        chan.exec_command(cmd)

        thread = threading.Thread(
            target=self._reader_loop,
            args=(iface, chan),
            name=f"candump-{iface}",
            daemon=True,
        )
        thread.start()
        self._readers.append(BusReader(iface=iface, channel=chan, thread=thread))
        self._on_status(f"Streaming {cmd}")

    def _push_raw(self, iface: str, text: str, stream: str) -> None:
        try:
            self.raw_queue.put_nowait({"bus": iface, "text": text, "stream": stream})
        except queue.Full:
            try:
                self.raw_queue.get_nowait()
                self.raw_queue.put_nowait({"bus": iface, "text": text, "stream": stream})
            except queue.Empty:
                pass

    def _reader_loop(self, iface: str, chan: paramiko.Channel) -> None:
        out_buf = b""
        err_buf = b""

        def _emit_lines(buf: bytes, stream: str) -> bytes:
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                # PTY-free output usually doesn't have \r, but strip it just in case.
                text = line.rstrip(b"\r").decode(errors="replace")
                if not text:
                    continue
                # Always emit the raw line — useful for debugging stderr,
                # auth errors, "Cannot find device", etc.
                self._push_raw(iface, text, stream)

                if stream != "out":
                    continue
                frame = parse_candump_line(text)
                if frame is None:
                    continue
                if not frame["bus"]:
                    frame["bus"] = iface
                try:
                    self.frame_queue.put_nowait(frame)
                except queue.Full:
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait(frame)
                    except queue.Empty:
                        pass
                if self._on_frame is not None:
                    try:
                        self._on_frame(frame)
                    except Exception:  # noqa: BLE001
                        log.exception("on_frame callback failed")
            return buf

        try:
            while not self._stop.is_set():
                progressed = False
                if chan.recv_ready():
                    chunk = chan.recv(4096)
                    if chunk:
                        out_buf += chunk
                        out_buf = _emit_lines(out_buf, "out")
                        progressed = True
                if chan.recv_stderr_ready():
                    chunk = chan.recv_stderr(4096)
                    if chunk:
                        err_buf += chunk
                        err_buf = _emit_lines(err_buf, "err")
                        progressed = True
                if not progressed:
                    if chan.exit_status_ready() and not chan.recv_ready() and not chan.recv_stderr_ready():
                        break
                    time.sleep(0.01)
        except (socket.error, EOFError) as exc:
            log.warning("reader %s closed: %s", iface, exc)
        finally:
            # Flush any trailing partial line.
            for buf, stream in ((out_buf, "out"), (err_buf, "err")):
                if buf:
                    text = buf.rstrip(b"\r").decode(errors="replace")
                    if text:
                        self._push_raw(iface, text, stream)
            try:
                chan.close()
            except Exception:  # noqa: BLE001
                pass
            self._on_status(f"Stream {iface} stopped.")

    def stop(self) -> None:
        self._stop.set()
        for r in self._readers:
            try:
                r.channel.close()
            except Exception:  # noqa: BLE001
                pass
        for r in self._readers:
            r.thread.join(timeout=2)
        self._readers.clear()
        if self._client:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001
                pass
            self._client = None
        self._on_status("Disconnected.")
