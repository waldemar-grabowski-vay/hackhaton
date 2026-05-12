"""T020 — DbcDecoder tests.

We don't ship a CI fixture DBC (cantools' parser needs valid syntax;
hand-rolling one is fragile). Instead we verify:

- `find_dbc()` against an empty repo returns None.
- `find_dbc()` finds a DBC under one of the configured glob patterns.
- A decoder with no DBC loaded returns frames with empty signals.
- `autoload()` falls back through (`explicit`, then `find_dbc()`); both
  branches handle a missing file gracefully via the `load_error` path.
"""

from __future__ import annotations

from pathlib import Path

from vayobd.live.dbc_decoder import DbcDecoder, find_dbc


def test_find_dbc_empty_repo(tmp_path: Path) -> None:
    assert find_dbc(tmp_path) is None


def test_find_dbc_finds_glob_match(tmp_path: Path) -> None:
    target = tmp_path / "platform" / "dbc" / "reecu-diag.dbc"
    target.parent.mkdir(parents=True)
    target.write_text("VERSION \"\"\n")  # not a valid DBC, but find_dbc only checks the glob
    found = find_dbc(tmp_path)
    assert found == target


def test_find_dbc_picks_most_recent(tmp_path: Path) -> None:
    older = tmp_path / "platform" / "dbc" / "older.dbc"
    newer = tmp_path / "ts" / "6_tools" / "CANoe_G4" / "DBCs" / "newer.dbc"
    older.parent.mkdir(parents=True)
    newer.parent.mkdir(parents=True)
    older.write_text("VERSION \"\"\n")
    newer.write_text("VERSION \"\"\n")
    # Make `newer` newer.
    import os
    import time

    older_time = time.time() - 100
    os.utime(older, (older_time, older_time))
    found = find_dbc(tmp_path)
    assert found == newer


def test_decoder_returns_empty_signals_without_dbc() -> None:
    dec = DbcDecoder()
    frame = dec.decode(at_ms=1234, bus="can0", can_id=0x100, ext=False, data=b"\x00" * 8)
    assert frame.signals == {}
    assert frame.message_name is None


def test_autoload_with_missing_paths(tmp_path: Path) -> None:
    dec = DbcDecoder()
    ok = dec.autoload(dbc_search_root=tmp_path, explicit=tmp_path / "nope.dbc")
    assert ok is False
    assert dec.loaded is False
    assert dec.load_error is not None
