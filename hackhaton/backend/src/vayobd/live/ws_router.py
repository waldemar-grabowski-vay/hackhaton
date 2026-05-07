"""FastAPI WebSocket router for `/api/live/{host_id}/ws` (T023 — Phase 3 / US1 stub).

Validates the X-Vay-User header, the developer_mode_check query param,
and that `host_id` is in the in-scope inventory; on accept, instantiates
a `LiveDiagnosticSession` and runs it. Implementation lands in T023.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/live", tags=["live"])
