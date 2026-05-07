# Data Model — Real Diagnostic Engine via ree-debug-tui

Three layers, all derivable from one source of truth (the engine
crate's `serde`-derivable types):

1. **Rust** — `ree-debug-engine/src/types.rs`. Authoritative.
2. **Python** — Pydantic v2 models in `backend/src/vayobd/models.py`.
   Mirrors the Rust shapes; extends 001's `DiagnosticItem` /
   `CheckCategory` / `ItemStatus` enums.
3. **TypeScript** — Zod schemas in `frontend/src/api/schemas.ts`.
   Mirrors the Pydantic models.

---

## Layer 1 — Rust (`ree-debug-engine/src/types.rs`)

```rust
use serde::{Deserialize, Serialize};

/// Stable identifier for a host, matching the regex in `001-host-diagnostics`.
/// Validated at deserialise time via a `serde(deserialize_with = …)` helper.
pub type HostId = String;

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum HostType {
    Vehicle,
    Telestation,
}

/// Per-check status as the engine sees it (engineering truth).
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum CheckStatus {
    Pass,
    Warn,
    Fail,
}

/// Run-level outcome the CLI binary computes from per-check distribution
/// + the SSH layer's reachability signal.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum RunOutcome {
    Complete,
    Partial,
    Unreachable,
    Timeout,
}

/// One thing that was checked.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckEntry {
    /// Stable identifier — the catalog key on the Python side.
    pub id: String,
    pub status: CheckStatus,
    /// Free-form raw output. PII-scrubbed by the Python side before persistence.
    pub raw_detail: Option<String>,
    pub duration_ms: u64,
}

/// What `ree-debug-cli` prints to stdout for one host run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineReport {
    /// Always "ree-debug-engine" — sanity flag for the Python side's parser.
    pub schema: String,
    /// Build-time git SHA. Drives FR-003a / FR-007 startup compatibility check.
    pub version: String,
    pub host_id: HostId,
    pub host_type: HostType,
    pub started_at: String,    // ISO 8601 UTC
    pub completed_at: String,  // ISO 8601 UTC
    pub outcome: RunOutcome,
    pub checks: Vec<CheckEntry>,
}

/// Engine-internal failure (broken inventory, host id not in inventory, SSH
/// startup crashed). Emitted as a separate JSON shape on stderr; the binary
/// exits non-zero.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineError {
    pub kind: EngineErrorKind,
    pub message: String,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum EngineErrorKind {
    InventoryMissing,
    InventoryUnparseable,
    UnknownHostId,
    SshStartupFailed,
    Internal,
}

pub async fn run_checks(
    host_id: &str,
    inventory_path: &std::path::Path,
) -> Result<EngineReport, EngineError> { /* ... */ }
```

**Validation rules** (enforced via `serde` custom deserialisers and
in `lib.rs`):
- `EngineReport.host_id` matches `^(ve|ts)-de(-[a-z0-9-]+)+$`.
- `EngineReport.checks` is non-empty when `outcome == Complete | Partial`.
- `EngineReport.checks` is empty when `outcome == Unreachable | Timeout`.
- `CheckEntry.id` is `[a-z0-9_]+`, max 64 chars.
- `CheckEntry.duration_ms` ≥ 0.

---

## Layer 2 — Python (Pydantic v2 in `backend/src/vayobd/models.py`)

001's existing `models.py` is **extended**, not replaced. New /
modified types:

```python
from enum import StrEnum

class CheckCategory(StrEnum):
    COMMUNICATION = "communication"
    HARDWARE = "hardware"
    CONFIGURATION = "configuration"
    SOFTWARE = "software"        # NEW (FR-006)
    CALIBRATION = "calibration"  # NEW (FR-006)


class ItemStatus(StrEnum):
    WORKING = "working"
    WARNING = "warning"          # NEW (FR-004a)
    ERROR = "error"


# DiagnosticItem keeps its existing shape; the validator is updated:
class DiagnosticItem(BaseModel):
    id: str
    name_key: str
    description_key: str | None
    category: CheckCategory
    status: ItemStatus
    recommended_action_key: str | None
    raw_detail: str | None

    @model_validator(mode="after")
    def _validate(self) -> DiagnosticItem:
        # Updated: warning items must also carry a recommended_action_key (FR-004b).
        if self.status in (ItemStatus.ERROR, ItemStatus.WARNING) and self.recommended_action_key is None:
            raise ValueError(
                f"item {self.id!r} with status {self.status} must have recommended_action_key"
            )
        return self
```

New types specific to the engine integration:

```python
class EngineStatus(StrEnum):
    """Mirrors the Rust CheckStatus enum."""
    PASS = "Pass"
    WARN = "Warn"
    FAIL = "Fail"


class EngineCheckEntry(BaseModel):
    id: str
    status: EngineStatus
    raw_detail: str | None = None
    duration_ms: int


class EngineReport(BaseModel):
    """Mirrors the Rust EngineReport. Parsed from ree-debug-cli stdout."""
    schema_: str = Field(alias="schema")    # "ree-debug-engine"
    version: str                            # build-time git SHA
    host_id: str
    host_type: HostType
    started_at: datetime
    completed_at: datetime
    outcome: RunOutcome
    checks: list[EngineCheckEntry]

    @model_validator(mode="after")
    def _validate(self) -> EngineReport:
        if self.schema_ != "ree-debug-engine":
            raise ValueError(f"unexpected schema marker {self.schema_!r}")
        return self


# The status-mapping table. Lives in checks/ree_cli.py beside ReeCliExecutor:
ENGINE_STATUS_TO_ITEM_STATUS: dict[EngineStatus, ItemStatus] = {
    EngineStatus.PASS: ItemStatus.WORKING,
    EngineStatus.WARN: ItemStatus.WARNING,
    EngineStatus.FAIL: ItemStatus.ERROR,
}
```

The catalog grows from 001's two-host-class table to one keyed by
engine check id:

```python
@dataclass(frozen=True)
class CheckSpec:
    id: str                                     # the engine's stable id
    host_classes: frozenset[str]                # which host classes run this check
    name_key: str                               # strings.ts key
    category: CheckCategory                     # one of FR-006's five
    description_key_pass: str | None
    description_key_warn: str | None
    description_key_fail: str | None
    recommended_action_key: str | None          # required when warn/fail are possible

# CATALOG: dict[str, CheckSpec]  — order ~25 entries. Source of truth for
# Constitution III's jargon audit (SC-003).
```

**Inventory shape** (`org/vay/inventory.yaml`) — Ansible-style
nested document, owned by the `ree-vehicle-configs` repo. Confirmed
by inspection of the operator's local clone:

```yaml
all:
  children:
    telestations:
      hosts:
        ts-de-ber-zeus:
          ansible_host: 192.168.60.2
        ts-de-ber-apollo:
          ansible_host: 192.168.20.2
        # ...
    vehicles:
      hosts:
        ve-de-apollo:
          ansible_host: 10.0.1.5
        # ...
```

The loader (`backend/src/vayobd/inventory/loader.py` rewrite) walks
`all.children.{telestations,vehicles}.hosts` and produces a `Host`
per nested key. `host.id` = the YAML key; `host.address` =
`ansible_host`; `host.type` is implied by the parent
(`telestations` → telestation, `vehicles` → vehicle); `host.country`
+ `host.city` are extracted from the `host.id` regex per
`001-host-diagnostics`'s rules. Non-`de` rows are dropped at load
time, same as 001. Belgium / US hosts (if any sneak into the file)
never reach the API surface. The
`InventoryMeta` Pydantic model from 001 is **slimmed**:

```python
class InventoryMeta(BaseModel):
    """Reduced from 001 — no last_refresh_attempted_at, no
    consecutive_failed_refreshes, since the cache layer is retired."""
    last_read_at: datetime    # always 'now' on reads (per FR-013a)
    source_path: str
    host_count: int
```

**Settings shape** (`~/.config/vayobd/settings.toml`):

```toml
[inventory]
path = "/home/operator/GitHub/ree-vehicle-configs"
```

```python
class InventorySettings(BaseModel):
    path: Path

    @field_validator("path", mode="after")
    def _expand_and_validate(cls, p: Path) -> Path:
        p = p.expanduser().resolve()
        if not p.is_dir():
            raise ValueError("path_not_a_directory")
        if not (p / "org" / "vay" / "inventory.yaml").is_file():
            raise ValueError("inventory_yaml_missing")
        return p


class AppSettings(BaseModel):
    inventory: InventorySettings | None = None  # None = first-launch state
```

---

## Layer 3 — TypeScript (Zod in `frontend/src/api/schemas.ts`)

Three changes:

```ts
// FR-004a — three-status enum, replacing 001's two-status enum.
export const itemStatusSchema = z.enum(["working", "warning", "error"]);
export type ItemStatus = z.infer<typeof itemStatusSchema>;

// FR-006 — five-category enum, replacing 001's three-category enum.
export const checkCategorySchema = z.enum([
  "communication",
  "hardware",
  "configuration",
  "software",
  "calibration",
]);
export type CheckCategory = z.infer<typeof checkCategorySchema>;

// FR-004b — warning items also need recommended_action_key.
export const diagnosticItemSchema = z
  .object({
    id: z.string(),
    name_key: z.string(),
    description_key: z.string().nullable(),
    category: checkCategorySchema,
    status: itemStatusSchema,
    recommended_action_key: z.string().nullable(),
    raw_detail: z.string().nullable(),
  })
  .superRefine((item, ctx) => {
    if (
      (item.status === "error" || item.status === "warning") &&
      item.recommended_action_key === null
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "warning/error items must have recommended_action_key",
        path: ["recommended_action_key"],
      });
    }
  });
```

New schema for the settings flow:

```ts
export const inventorySettingsSchema = z.object({
  path: z.string().min(1),
});

export const appSettingsSchema = z.object({
  inventory: inventorySettingsSchema.nullable(),
  // engine_mode is "live" | "fixture", surfaced via the EngineModeBadge.
  engine_mode: z.enum(["live", "fixture"]),
});

export const settingsErrorSchema = z.object({
  error: z.enum([
    "path_missing",
    "path_not_a_directory",
    "inventory_yaml_missing",
    "inventory_yaml_unparseable",
    "inventory_yaml_empty",
  ]),
  message_key: z.string(),
});
```

The 001 `InventoryMeta` schema is slimmed in lockstep with the
Pydantic side.

---

## Persistence shapes

| What | Location | Format | Owner |
|---|---|---|---|
| Operator settings | `~/.config/vayobd/settings.toml` | TOML | Backend (`settings_file.py`) |
| Run records | `~/.cache/vayobd/runs/<operator-slug>/<host_id>.json` | JSON | Backend (unchanged from 001 except for the `engine_version` audit field below) |
| Engine binary | `engine/target/release/ree-debug-cli` | ELF/Mach-O | Cargo build |
| Inventory file | `${inventory.path}/org/vay/inventory.yaml` | YAML | Operator (clones `ree-vehicle-configs`) |

Run records gain one field for forensics:

```json
{
  "host_id": "ve-de-apollo",
  "started_at": "...",
  "completed_at": "...",
  "outcome": "complete",
  "items": [...],
  "triggered_by": {"username": "...", "slug": "..."},
  "engine_version": "9697a5e"   /* NEW — git SHA the engine was built from */
}
```

---

## State transitions

Same as 001's `runner.py` lock state machine, with the executor
swapped:

```text
[idle] ──POST /api/runs──▶ [running] ──cli ok──▶ [parsing JSON] ──┬─▶ [complete | partial]
                              │                                     │
                              │                                     └─▶ [unreachable]   (on parse error)
                              │
                              └─cli != 0 / SIGKILL──▶ [unreachable | timeout]
```

The per-`host_id` `asyncio.Lock` from 001 (FR-011) still owns the
`[idle] → [running]` transition. The CLI binary's own SSH layer
manages its ControlMaster lifecycle internally.
