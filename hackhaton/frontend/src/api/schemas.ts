/**
 * Zod schemas mirroring backend/src/vayobd/models.py. Source of truth for the
 * API boundary at runtime — every fetch goes through `client.ts` which calls
 * `.parse(...)` on the response.
 */
import { z } from "zod";

export const hostIdSchema = z
  .string()
  .regex(/^(ve|ts)-de(-[a-z0-9-]+)+$/, "invalid host id");

export const countrySchema = z.enum(["de"]);
export type Country = z.infer<typeof countrySchema>;

export const hostTypeSchema = z.enum(["vehicle", "telestation"]);
export type HostType = z.infer<typeof hostTypeSchema>;

// 002 / FR-006 — five-category palette pinned by the 2026-05-07 clarify
// session. Software covers vDrive manifest drift / firmware / gateware /
// container status; Calibration covers SAS calibration + GNSS yaw-rate
// watchdog.
export const checkCategorySchema = z.enum([
  "communication",
  "hardware",
  "configuration",
  "software",
  "calibration",
]);
export type CheckCategory = z.infer<typeof checkCategorySchema>;

// 002 / FR-004a — three-status enum, replacing 001's two-status enum.
// Mapped from the engine's `Pass | Warn | Fail`.
export const itemStatusSchema = z.enum(["working", "warning", "error"]);
export type ItemStatus = z.infer<typeof itemStatusSchema>;

export const runOutcomeSchema = z.enum([
  "complete",
  "partial",
  "unreachable",
  "timeout",
]);
export type RunOutcome = z.infer<typeof runOutcomeSchema>;

export const hostSchema = z
  .object({
    id: hostIdSchema,
    display_name: z.string(),
    host_class: z.string(),
    type: hostTypeSchema,
    country: countrySchema,
    city: z.string().nullable(),
  })
  .superRefine((host, ctx) => {
    if (host.type === "vehicle" && host.city !== null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "vehicles must not carry a city",
        path: ["city"],
      });
    }
    if (host.type === "telestation" && host.city === null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "telestations must carry a city",
        path: ["city"],
      });
    }
  });
export type Host = z.infer<typeof hostSchema>;

// 002 / FR-013a — slimmed for 002. The cache + periodic-refresh layer
// from 001 (and its `last_refresh_attempted_at` /
// `consecutive_failed_refreshes` fields) is retired; the inventory is
// re-read per request, so freshness IS "now" by definition.
export const inventoryMetaSchema = z.object({
  last_read_at: z.string().datetime({ offset: true }),
  source_path: z.string(),
  host_count: z.number().int().nonnegative(),
});
export type InventoryMeta = z.infer<typeof inventoryMetaSchema>;

export const inventorySchema = z.object({
  meta: inventoryMetaSchema,
  hosts: z.array(hostSchema),
});
export type Inventory = z.infer<typeof inventorySchema>;

// 002 / FR-004b — `warning` items also require `recommended_action_key`,
// matching the parity rule between `warning` and `error` rendering in
// the "Needs attention" group.
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
        message:
          "warning/error items must have recommended_action_key (002 FR-004b)",
        path: ["recommended_action_key"],
      });
    }
  });
export type DiagnosticItem = z.infer<typeof diagnosticItemSchema>;

export const diagnosticRunSchema = z.object({
  host_id: hostIdSchema,
  started_at: z.string().datetime({ offset: true }),
  completed_at: z.string().datetime({ offset: true }),
  outcome: runOutcomeSchema,
  items: z.array(diagnosticItemSchema),
});
export type DiagnosticRun = z.infer<typeof diagnosticRunSchema>;

export const problemDetailSchema = z.object({
  error: z.string(),
  message_key: z.string(),
});
export type ProblemDetail = z.infer<typeof problemDetailSchema>;

export const runRequestSchema = z.object({
  host_id: hostIdSchema,
});
export type RunRequest = z.infer<typeof runRequestSchema>;

// --- 002 settings schemas (T021, FR-009 — FR-012) -------------------------

export const inventorySettingsSchema = z.object({
  path: z.string().min(1),
});
export type InventorySettings = z.infer<typeof inventorySettingsSchema>;

export const engineModeSchema = z.enum(["live", "fixture"]);
export type EngineMode = z.infer<typeof engineModeSchema>;

export const appSettingsSchema = z.object({
  inventory: inventorySettingsSchema.nullable(),
  engine_mode: engineModeSchema,
});
export type AppSettings = z.infer<typeof appSettingsSchema>;

// 002 / FR-007 + setup-card validation. The contract's structured
// error codes (contracts/http-api.md). `meta.path` echoes the offending
// path so the setup card can show it inline.
export const settingsErrorCodeSchema = z.enum([
  "path_missing",
  "path_not_a_directory",
  "inventory_yaml_missing",
  "inventory_yaml_unparseable",
  "inventory_yaml_empty",
]);
export type SettingsErrorCode = z.infer<typeof settingsErrorCodeSchema>;

export const settingsErrorSchema = z.object({
  error: settingsErrorCodeSchema,
  message_key: z.string(),
  meta: z.object({ path: z.string() }).optional(),
});
export type SettingsError = z.infer<typeof settingsErrorSchema>;
