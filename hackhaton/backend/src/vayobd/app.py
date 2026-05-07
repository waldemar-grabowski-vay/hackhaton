"""FastAPI app factory.

Mounts the API routers, the static SPA when present, the auth
dependency, and the error handlers. Single entry point:
`uvicorn vayobd.app:app --reload`.

Notable changes from 001:
- The periodic inventory refresh task is gone (FR-013a — inventory
  is re-read from disk per request, no caching).
- T035 startup self-check: when `VAYOBD_EXECUTOR=ree`, invoke
  `ree-debug-cli --version` once during the lifespan startup to
  prove the binary is reachable + cache the embedded SHA in
  `app.state.engine_mode` / `app.state.engine_version`. Failure
  surfaces via FR-007 (`engine_unavailable` / `engine_incompatible`)
  on the first run attempt.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from vayobd.api.errors import install_exception_handlers
from vayobd.api.inventory import router as inventory_router
from vayobd.api.runs import router as runs_router
from vayobd.config import ExecutorMode, Settings, get_settings
from vayobd.dependencies import _resolve_ree_cli_bin
from vayobd.logging import configure_logging, get_logger

log = get_logger(__name__)


async def _engine_self_check(settings: Settings) -> tuple[str, str | None]:
    """T035 / FR-003a / FR-007 — ree-debug-cli startup probe.

    Returns `(engine_mode, engine_version)`:
    - `engine_mode` ∈ {"live", "fixture", "engine_unavailable",
      "engine_incompatible"}.
    - `engine_version` is the SHA the binary self-reported, or
      None when the probe didn't succeed.
    """
    if settings.executor is not ExecutorMode.REE:
        return ("fixture", None)

    bin_path = _resolve_ree_cli_bin(settings)
    if bin_path is None:
        log.warning(
            "engine_unavailable",
            reason="ree-debug-cli not found",
            hint="cargo build --release --workspace from engine/, or set VAYOBD_REE_CLI_BIN",
        )
        return ("engine_unavailable", None)

    try:
        proc = await asyncio.create_subprocess_exec(
            str(bin_path),
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
    except (TimeoutError, OSError) as exc:
        log.warning("engine_incompatible", binary=str(bin_path), error=str(exc))
        return ("engine_incompatible", None)

    if proc.returncode != 0:
        log.warning(
            "engine_incompatible",
            binary=str(bin_path),
            exit_code=proc.returncode,
        )
        return ("engine_incompatible", None)

    version = stdout.decode("utf-8", errors="replace").strip()
    # `ree-debug-cli --version` prints `ree-debug-cli <sha>`.
    sha = version.split()[-1] if version else None
    log.info("engine_ready", binary=str(bin_path), version=sha)
    return ("live", sha)


def _make_lifespan(settings: Settings):
    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging()
        log.info("vayobd_starting", executor=settings.executor.value)
        mode, version = await _engine_self_check(settings)
        app.state.engine_mode = mode
        app.state.engine_version = version
        try:
            yield
        finally:
            log.info("vayobd_stopped")

    return _lifespan


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title="VayOBD Tool",
        version="0.1.0",
        lifespan=_make_lifespan(settings),
    )

    install_exception_handlers(app)

    app.include_router(inventory_router)
    app.include_router(runs_router)

    @app.get("/api/health", tags=["meta"])
    def _health() -> dict[str, str | None]:
        engine_mode = getattr(app.state, "engine_mode", "unknown")
        engine_version = getattr(app.state, "engine_version", None)
        return {
            "status": "ok",
            "version": app.version,
            "engine_mode": engine_mode,
            "engine_version": engine_version,
        }

    if settings.static_dir is not None and settings.static_dir.exists():
        app.mount(
            "/",
            StaticFiles(directory=str(settings.static_dir), html=True),
            name="spa",
        )

    return app


app = create_app()
