"""FastAPI app factory.

Mounts the API routers, the static SPA when present, the auth
dependency, and the error handlers. Single entry point:
`uvicorn vayobd.app:app --reload`.

Notable change from 001: the periodic inventory refresh task is gone
(FR-013a — inventory is re-read from disk per request, no caching).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from vayobd.api.errors import install_exception_handlers
from vayobd.api.inventory import router as inventory_router
from vayobd.api.runs import router as runs_router
from vayobd.config import Settings, get_settings
from vayobd.logging import configure_logging, get_logger

log = get_logger(__name__)


def _make_lifespan(_settings: Settings):
    @asynccontextmanager
    async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
        configure_logging()
        log.info("vayobd_starting")
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
