"""SSH+candump async subprocess wrapper (T021 — Phase 3 / US1 stub).

Spawns the operator's local `ssh` to stream `candump` from the chosen
testbed; emits `(at_ms, can_id, dlc, payload_bytes)` tuples on a queue.

Implementation lands in T021 (Phase 3, US1). The skeleton lives here so
the import graph compiles ahead of US1 work.
"""

from __future__ import annotations
