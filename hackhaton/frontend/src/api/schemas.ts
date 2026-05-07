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

export const checkCategorySchema = z.enum([
  "communication",
  "hardware",
  "configuration",
]);
export type CheckCategory = z.infer<typeof checkCategorySchema>;

export const itemStatusSchema = z.enum(["working", "error"]);
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

export const inventoryMetaSchema = z.object({
  last_refreshed_at: z.string().datetime({ offset: true }),
  // FR-027 — distinct from `last_refreshed_at`; tracks the most recent
  // refresh attempt (success or failure) so the SPA banner can stay current.
  last_refresh_attempted_at: z.string().datetime({ offset: true }).nullable(),
  consecutive_failed_refreshes: z.number().int().nonnegative(),
  source_revision: z.string(),
  host_count: z.number().int().nonnegative(),
});
export type InventoryMeta = z.infer<typeof inventoryMetaSchema>;

export const inventorySchema = z.object({
  meta: inventoryMetaSchema,
  hosts: z.array(hostSchema),
});
export type Inventory = z.infer<typeof inventorySchema>;

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
    if (item.status === "error" && item.recommended_action_key === null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "errored item must have recommended_action_key (FR-005)",
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
