"""ERRQ model loader (T009).

Ports `TS_diagnostic_tool/errq_bridge.py` to a per-process module that:

- loads the user's local `errq.py` from
  `<settings.ree_reecu_path>/platform/tools/errq/errq.py` once at backend
  startup, falling back to a small set of conventional sub-paths;
- caches the model in an `ErrqModel` dataclass; concurrent live sessions
  share the model read-only (no global module state to race on, unlike
  the desktop tool);
- exposes `decode_buffer(channel, data) -> list[ErrqResult]` for use by
  `ErrqStateTracker`;
- gracefully degrades: if the clone is missing, returns an `ErrqModel`
  with `model is None`. Sessions then surface the degraded-mode UI
  contract from FR-012.
"""

from __future__ import annotations

import importlib
import logging
import sys
import types
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class ErrqResult:
    code: int | str
    name: str | None
    description: str
    severity: str | None = None
    byte: int = 0
    bit: int = 0
    raw: Any = None


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


@dataclass
class ErrqModel:
    """Runtime handle to the loaded errq model. `model is None` means
    degraded mode — callers MUST surface the FR-012 message and skip
    decoding. The errq Python module is kept around because
    `decode_errors` and the `EventConfigurations` types live on it.
    """

    model: Any
    module: types.ModuleType | None
    loaded_at: datetime
    source_path: Path
    load_error: str | None = None

    @property
    def loaded(self) -> bool:
        return self.model is not None and self.module is not None

    def decode_buffer(self, channel: str, data: bytes) -> list[ErrqResult]:
        """Decode a 64-byte ERRQ buffer for one TS channel ("A"/"B").

        Walks each non-zero byte through `errq.decode_errors(model, byte,
        value)` to expand the bit-mask into a list of EventConfigurations,
        then wraps each one as an `ErrqResult`.
        """
        if not self.loaded:
            return []
        decode_fn = getattr(self.module, "decode_errors", None)
        if not callable(decode_fn):
            log.warning("errq.decode_errors() missing — version mismatch?")
            return []

        out: list[ErrqResult] = []
        for i, value in enumerate(data):
            if value == 0:
                continue
            byte_1based = i + 1
            try:
                errors = decode_fn(self.model, byte_1based, value)
            except ValueError as exc:
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


def _import_errq_module(target_dir: Path, repo_root: Path) -> tuple[types.ModuleType | None, str | None]:
    """Load `errq.py` via importlib, with a `from __future__ import
    annotations` shim so PEP-604 union syntax doesn't break on Python
    <3.10 (defensive — we already require 3.11 but the desktop tool
    bundles for 3.9 and the shim is harmless on newer interpreters).
    """
    py_file = target_dir / "errq.py"
    if not py_file.is_file():
        return None, f"errq.py not found at {py_file}"

    for p in (repo_root, target_dir, target_dir.parent):
        sp = str(p)
        try:
            if Path(sp).exists() and sp not in sys.path:
                sys.path.insert(0, sp)
        except OSError:
            continue

    try:
        src = py_file.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"cannot read errq.py: {exc!r}"

    if "from __future__ import annotations" not in src:
        src = "from __future__ import annotations\n" + src

    mod = types.ModuleType("errq")
    mod.__file__ = str(py_file)
    mod.__name__ = "errq"
    try:
        code = compile(src, str(py_file), "exec")
        exec(code, mod.__dict__)  # noqa: S102
    except SyntaxError as exc:
        return None, f"errq.py syntax error at line {exc.lineno}: {exc.msg}"
    except Exception as exc:  # noqa: BLE001
        return None, f"errq.py import error: {exc!r}"

    sys.modules["errq"] = mod
    return mod, None


def load_errq_model(ree_reecu_path: Path) -> ErrqModel:
    """Load the errq model from the operator's `ree-reecu` clone.

    Returns an `ErrqModel` either fully loaded or in degraded mode (with
    `model is None` and a populated `load_error`). Never raises.
    """
    target = (ree_reecu_path / "platform" / "tools" / "errq").expanduser()
    log.info("errq: trying to load from %s", target)

    if not target.exists():
        msg = (
            f"errq tool directory not found at {target}; configure "
            "VAYOBD_REE_REECU_PATH or [live].ree_reecu_path in settings."
        )
        log.warning(msg)
        return ErrqModel(
            model=None,
            module=None,
            loaded_at=datetime.now(timezone.utc),
            source_path=target,
            load_error=msg,
        )

    module, err = _import_errq_module(target, ree_reecu_path)
    if module is None:
        return ErrqModel(
            model=None,
            module=None,
            loaded_at=datetime.now(timezone.utc),
            source_path=target,
            load_error=err,
        )

    build_model = getattr(module, "build_model", None)
    if not callable(build_model):
        return ErrqModel(
            model=None,
            module=module,
            loaded_at=datetime.now(timezone.utc),
            source_path=target,
            load_error="errq.py is loaded but exposes no build_model() — version mismatch?",
        )

    try:
        model = build_model("ts")
    except FileNotFoundError as exc:
        msg = (
            f"errq build_model('ts') failed — missing CSV file: {exc.filename or exc}. "
            "Ensure the ree-reecu repo is fully cloned (TS Errq CSVs live under "
            "ts/6_tools/TS_Generators/Errq/ts_errq_cfg_generator/csv/)."
        )
        log.warning(msg)
        return ErrqModel(
            model=None,
            module=module,
            loaded_at=datetime.now(timezone.utc),
            source_path=target,
            load_error=msg,
        )
    except Exception as exc:  # noqa: BLE001
        return ErrqModel(
            model=None,
            module=module,
            loaded_at=datetime.now(timezone.utc),
            source_path=target,
            load_error=f"errq build_model('ts') raised: {exc!r}",
        )

    log.info(
        "errq: model loaded with %d errors, %d groups",
        len(getattr(model, "errors", []) or []),
        len(getattr(model, "error_groups", []) or []),
    )
    return ErrqModel(
        model=model,
        module=module,
        loaded_at=datetime.now(timezone.utc),
        source_path=target,
    )
