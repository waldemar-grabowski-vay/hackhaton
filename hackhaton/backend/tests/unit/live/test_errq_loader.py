"""T019 — ErrqModel loader tests, focused on the degraded-mode contract.

The happy path (full ree-reecu clone present) is exercised via the
quickstart manual smoke; in CI we don't have the clone, so we verify
the loader returns a degraded `ErrqModel` rather than raising.
"""

from __future__ import annotations

from pathlib import Path

from vayobd.live.errq_loader import load_errq_model


def test_missing_clone_returns_degraded_model(tmp_path: Path) -> None:
    """The configured clone path doesn't exist on disk."""
    model = load_errq_model(tmp_path / "does-not-exist")
    assert model.loaded is False
    assert model.model is None
    assert model.module is None
    assert model.load_error is not None
    assert "errq tool directory not found" in model.load_error


def test_clone_without_errq_returns_degraded(tmp_path: Path) -> None:
    """Clone exists but the platform/tools/errq subdir is missing."""
    (tmp_path / "platform" / "tools").mkdir(parents=True)
    model = load_errq_model(tmp_path)
    assert model.loaded is False
    assert "errq tool directory not found" in (model.load_error or "")


def test_decode_buffer_returns_empty_in_degraded_mode(tmp_path: Path) -> None:
    model = load_errq_model(tmp_path / "missing")
    assert model.decode_buffer("A", bytes([0x01] + [0] * 63)) == []
