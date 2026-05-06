"""FastAPI app factory (T017).

Mounts the API routers, the static SPA when present, the auth middleware,
the error handlers, and the periodic inventory refresh (T019). Single
entry point: `uvicorn vayobd.app:app --reload`.
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
from vayobd.config import Settings, get_settings
from vayobd.inventory.scheduler import run_periodic_refresh
from vayobd.logging import configure_logging, get_logger

log = get_logger(__name__)


def _make_lifespan(settings: Settings):
    @asynccontextmanager
    async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
        configure_logging()
        log.info("vayobd_starting")
        refresh_task = asyncio.create_task(
            run_periodic_refresh(
                inventory_path=settings.inventory_path,
                branch=settings.inventory_branch,
                meta_path=settings.inventory_meta_path,
                interval_seconds=settings.refresh_interval_seconds,
            ),
            name="vayobd-inventory-refresh",
        )
        try:
            yield
        finally:
            refresh_task.cancel()
            try:
                await refresh_task
            except (asyncio.CancelledError, Exception):
                pass
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
    def _health() -> dict[str, str]:
        return {"status": "ok", "version": app.version}

    if settings.static_dir is not None and settings.static_dir.exists():
        app.mount(
            "/",
            StaticFiles(directory=str(settings.static_dir), html=True),
            name="spa",
        )

    return app


app = create_app()
