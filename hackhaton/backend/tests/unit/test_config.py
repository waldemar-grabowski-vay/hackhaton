"""T057 — settings.toml is layered into runtime Settings.

Confirms the precedence order documented in `config.get_settings`:
env vars > .env > settings.toml [live] block > class defaults. The
`get_settings` lru_cache is cleared between tests so each call reads
afresh.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vayobd import config


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


@pytest.fixture
def isolated_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point XDG_CONFIG_HOME at a tmp dir so tests don't trample the
    operator's real settings.toml.
    """
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    # Strip any inherited VAYOBD_* env vars so tests start clean.
    for name in list(os.environ):
        if name.startswith("VAYOBD_"):
            monkeypatch.delenv(name, raising=False)
    return tmp_path / "vayobd" / "settings.toml"


import os  # placed here so the fixture above can use monkeypatch.setenv first


def test_no_toml_file_returns_class_defaults(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No settings.toml on disk → Settings() defaults pass through."""
    assert not isolated_xdg.exists()
    s = config.get_settings()
    assert s.developer_mode is False
    assert s.dbc_path is None
    assert s.channel_a_pattern == r"(?i)_CHA_|TS_CHA"


def test_toml_file_overrides_class_defaults(
    isolated_xdg: Path, tmp_path: Path
) -> None:
    """A settings.toml `[live]` block must lift values into the runtime
    Settings.
    """
    isolated_xdg.parent.mkdir(parents=True, exist_ok=True)
    isolated_xdg.write_text(
        '[live]\n'
        'developer_mode = true\n'
        f'dbc_path = "{tmp_path}/my.dbc"\n'
        'channel_a_pattern = "^chA_"\n'
        'channel_b_pattern = "^chB_"\n'
    )

    s = config.get_settings()
    assert s.developer_mode is True
    assert s.dbc_path == tmp_path / "my.dbc"
    assert s.channel_a_pattern == "^chA_"
    assert s.channel_b_pattern == "^chB_"


def test_env_var_beats_toml(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Pydantic-settings precedence: env vars must override the TOML
    layer.
    """
    isolated_xdg.parent.mkdir(parents=True, exist_ok=True)
    isolated_xdg.write_text(
        '[live]\n'
        'channel_a_pattern = "from_toml"\n'
    )
    monkeypatch.setenv("VAYOBD_CHANNEL_A_PATTERN", "from_env")

    s = config.get_settings()
    assert s.channel_a_pattern == "from_env"


def test_malformed_toml_falls_back_to_defaults(
    isolated_xdg: Path,
) -> None:
    """A broken TOML must NOT prevent backend startup — fail soft to
    class defaults.
    """
    isolated_xdg.parent.mkdir(parents=True, exist_ok=True)
    isolated_xdg.write_text("[live\nbroken")

    s = config.get_settings()
    # Falls back to defaults (developer_mode False, default channel pattern).
    assert s.developer_mode is False
    assert s.channel_a_pattern == r"(?i)_CHA_|TS_CHA"
