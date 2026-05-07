"""
Bridge to the local `errq` tool at REPO_ROOT/platform/tools/errq.

Uses the real API exposed by `errq.py`:

    model = errq.build_model("ts")              # loads CSVs, ~220 errors
    errs  = errq.decode_errors(model, byte, value)
            # byte is 1-based, value is the byte's raw value treated as a
            # bit-mask. Each set bit corresponds to one EventConfigurations
            # whose .errorId is the symbolic name (e.g. "TS_FOO_BAR_ERR").

Returned ErrqResult shape:
    code:        the bit value (1, 2, 4, 8, ...) that triggered this error
    name:        symbolic error id from the CSV
    description: error id (CSV `Description` column is empty in this repo)
    severity:    derived from associated error groups (best-effort)
    byte/bit:    where in the buffer it came from (1-based byte, bit index)
    raw:         the original EventConfigurations object for power users
"""
from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
import types
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from config import ERRQ_PATH, REPO_ROOT

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public data shape
# ---------------------------------------------------------------------------
@dataclass
class ErrqResult:
    code: int | str
    name: str | None
    description: str
    severity: str | None = None
    byte: int = 0
    bit: int = 0
    raw: Any = None

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
            "byte": self.byte,
            "bit": self.bit,
        }


# ---------------------------------------------------------------------------
# Module + model resolver
# ---------------------------------------------------------------------------
_ERRQ_PATH_OVERRIDE: Path | None = None
_MOD: Any = None
_MODEL: Any = None
_MODEL_LOAD_ERROR: str | None = None


def errq_path() -> Path:
    return _ERRQ_PATH_OVERRIDE or ERRQ_PATH


def set_errq_path(path: Path | str) -> None:
    """Override the errq directory and force a reload on next call."""
    global _ERRQ_PATH_OVERRIDE, _MOD, _MODEL, _MODEL_LOAD_ERROR
    _ERRQ_PATH_OVERRIDE = Path(str(path))
    _MOD = None
    _MODEL = None
    _MODEL_LOAD_ERROR = None
    translate.cache_clear()  # type: ignore[attr-defined]
    log.info("errq path overridden -> %s", _ERRQ_PATH_OVERRIDE)


def _import_errq_module() -> Any | None:
    """Load errq.py via importlib so its __file__ resolves under the user's repo."""
    global _MOD, _MODEL_LOAD_ERROR
    if _MOD is not None:
        return _MOD

    target = errq_path()
    log.info("errq: trying to load from %s", target)
    log.info("errq: REPO_ROOT=%s exists=%s", REPO_ROOT, REPO_ROOT.exists())
    log.info("errq: target dir exists=%s", target.exists())

    # Make sure absolute imports inside the module find their siblings.
    for p in (REPO_ROOT, target, target.parent):
        sp = str(p)
        try:
            if Path(sp).exists() and sp not in sys.path:
                sys.path.insert(0, sp)
                log.debug("errq: added to sys.path: %s", sp)
        except OSError:
            continue

    py_file = target / "errq.py"
    if not py_file.is_file():
        msg = f"errq.py not found at {py_file}"
        log.warning(msg)
        _MODEL_LOAD_ERROR = msg + " — use 'Browse errq...' to point at the right folder."
        return None

    log.info("errq: importing %s (with __future__ annotations shim)", py_file)
    # We deliberately DON'T use importlib.spec_from_file_location here.
    # errq.py uses PEP 604 union syntax (`Path | None`) which is a syntax
    # error on Python <3.10, and PyInstaller bundles often pin 3.9.
    # Reading the source and prepending `from __future__ import annotations`
    # makes all annotations lazy strings, which sidesteps the parse error
    # without requiring the user to upgrade Python or edit their repo.
    try:
        src = py_file.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        log.exception("errq: cannot read %s", py_file)
        _MODEL_LOAD_ERROR = f"cannot read errq.py: {exc!r}"
        return None

    if "from __future__ import annotations" not in src:
        # Inject after any leading docstring + comment block. Simplest safe
        # approach: prepend with an explicit \n so line numbers in
        # tracebacks shift by exactly one.
        src = "from __future__ import annotations\n" + src

    mod = types.ModuleType("errq")
    mod.__file__ = str(py_file)
    mod.__name__ = "errq"
    try:
        code = compile(src, str(py_file), "exec")
        exec(code, mod.__dict__)
    except SyntaxError as exc:
        log.exception("errq: SyntaxError parsing errq.py")
        _MODEL_LOAD_ERROR = (
            f"errq.py syntax error at line {exc.lineno}: {exc.msg}. "
            "If this looks like a Python version mismatch, the build "
            "machine probably needs Python 3.10+ — but the future-import "
            "shim should have handled most cases."
        )
        return None
    except Exception as exc:  # noqa: BLE001
        log.exception("errq: import failed")
        _MODEL_LOAD_ERROR = f"errq.py import error: {exc!r}"
        return None

    sys.modules["errq"] = mod
    _MOD = mod
    log.info("errq: imported OK from %s", py_file)
    return mod


def _get_model() -> Any | None:
    """Build (and cache) the TS errq model. Returns None on failure."""
    global _MODEL, _MODEL_LOAD_ERROR
    if _MODEL is not None:
        return _MODEL
    mod = _import_errq_module()
    if mod is None:
        _MODEL_LOAD_ERROR = (
            f"errq.py not found at {errq_path()}. Use 'Browse errq...' to point at the right folder."
        )
        return None
    if not hasattr(mod, "build_model"):
        _MODEL_LOAD_ERROR = "errq.py is loaded but exposes no build_model() — version mismatch?"
        log.warning(_MODEL_LOAD_ERROR)
        return None
    try:
        log.info("errq: calling build_model('ts')")
        if hasattr(mod, "get_errq_gen_dir"):
            try:
                expected_dir = mod.get_errq_gen_dir("ts")
                log.info("errq: build_model will read CSVs from %s", expected_dir)
                if not expected_dir.exists():
                    log.warning("errq: CSV dir does not exist: %s", expected_dir)
            except Exception as exc:  # noqa: BLE001
                log.debug("errq: get_errq_gen_dir() probe failed: %s", exc)
        _MODEL = mod.build_model("ts")
    except FileNotFoundError as exc:
        _MODEL_LOAD_ERROR = (
            f"errq build_model('ts') failed: missing CSV file: {exc.filename or exc}. "
            "Make sure the ree-reecu repo is fully cloned (the CSVs live under "
            "ts/6_tools/TS_Generators/Errq/ts_errq_cfg_generator/csv/)."
        )
        log.warning(_MODEL_LOAD_ERROR)
        return None
    except Exception as exc:  # noqa: BLE001
        _MODEL_LOAD_ERROR = f"errq build_model('ts') raised: {exc!r}"
        log.exception("errq: build_model failed")
        return None
    log.info("errq: model loaded with %d errors, %d groups", len(_MODEL.errors), len(_MODEL.error_groups))
    return _MODEL


# Severity heuristic — best-effort grouping based on group names.
_GROUPS_CRITICAL = ("IMMEDIATE_PULLOVER", "SAFETY", "TS_BRAKES", "TS_STEERING")
_GROUPS_ERROR = ("ERROR_GROUP", "TS_THROTTLE")
_GROUPS_WARN = ("INIT", "STEERING_SENSORS_INVALID_MESSAGE", "TD_NEXT_SAFE_STOP", "NORMAL")


def _severity_for_error(err_config: Any) -> str | None:
    try:
        group_ids = [g.id for g in err_config.associatedEventGroups]
    except AttributeError:
        return None
    if not group_ids:
        return None
    joined = " ".join(group_ids).upper()
    for token in _GROUPS_CRITICAL:
        if token in joined:
            return "critical"
    for token in _GROUPS_ERROR:
        if token in joined:
            return "error"
    for token in _GROUPS_WARN:
        if token in joined:
            return "warn"
    return "info"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def model_status() -> str | None:
    """None if the model is loaded; otherwise a human-readable error string."""
    if _get_model() is None:
        return _MODEL_LOAD_ERROR or "errq model not loaded"
    return None


def is_resolved() -> bool:
    return _get_model() is not None


def decode_errq_buffer(channel: str, data: bytes) -> list[ErrqResult]:
    """
    Decode a 64-byte ERRQ buffer for one TS channel ("A" or "B").

    Walks each non-zero byte through errq.decode_errors(model, byte, value)
    to expand the bit-mask into a list of EventConfigurations, then wraps
    each one as an ErrqResult ready for display.
    """
    model = _get_model()
    mod = _MOD  # set by _get_model() if it succeeded
    if model is None or mod is None:
        return []

    decode_fn = getattr(mod, "decode_errors", None)
    if not callable(decode_fn):
        log.warning("errq.decode_errors() missing — version mismatch?")
        return []

    out: list[ErrqResult] = []
    for i, value in enumerate(data):
        if value == 0:
            continue
        byte_1based = i + 1
        try:
            errors = decode_fn(model, byte_1based, value)
        except ValueError as exc:
            # Out-of-range byte: aggregator might pass 64 bytes but the
            # model only knows up to (len(errors)//8)+1 bytes. Skip silently.
            log.debug("decode_errors(byte=%d, val=0x%02X): %s", byte_1based, value, exc)
            continue
        except Exception as exc:  # noqa: BLE001
            log.exception("decode_errors failed: %s", exc)
            continue

        for err in errors:
            err_id = getattr(err, "errorId", None) or "<unknown>"
            extra_desc = getattr(err, "description", "") or ""
            severity = _severity_for_error(err)
            description = err_id if not extra_desc else f"{err_id} — {extra_desc}"
            out.append(
                ErrqResult(
                    code=getattr(err, "bit", 0) or 0,
                    name=err_id,
                    description=description,
                    severity=severity,
                    byte=byte_1based,
                    bit=getattr(err, "bit", 0) or 0,
                    raw=err,
                )
            )
    return out


@lru_cache(maxsize=4096)
def translate(code: int | str) -> ErrqResult:
    """
    Single-code translation — left in for the legacy "TS_ERR_RESP" path.

    Looks up the error by its 0-based index inside the model. Most callers
    should use decode_errq_buffer() instead, which expands bit-masks
    correctly.
    """
    model = _get_model()
    if model is None or not isinstance(code, int):
        return ErrqResult(
            code=code,
            name=None,
            description=f"Unknown error 0x{code:X}" if isinstance(code, int) else f"Unknown error {code}",
            severity=None,
        )
    try:
        err = model.get_error_by_idx(code)
    except (AssertionError, KeyError, IndexError):
        return ErrqResult(
            code=code,
            name=None,
            description=f"No errq entry for index {code}",
            severity=None,
        )
    return ErrqResult(
        code=code,
        name=getattr(err, "errorId", None),
        description=getattr(err, "errorId", "") or "",
        severity=_severity_for_error(err),
        byte=getattr(err, "byte", 0) or 0,
        bit=getattr(err, "bit", 0) or 0,
        raw=err,
    )


def translate_array(channel: str, data: bytes) -> list[ErrqResult]:
    """Back-compat alias for the aggregator."""
    return decode_errq_buffer(channel, data)
