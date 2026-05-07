/**
 * Zod schemas for the live diagnostic WebSocket envelopes (T012).
 *
 * Mirrors `backend/src/vayobd/live/live_models.py`. Both sides validate
 * — backend with Pydantic, frontend with Zod — and unknown `kind` values
 * are silently dropped on the receiving side.
 *
 * The matching wire contract lives in
 * `specs/004-ts-diag-browser/contracts/websocket.md`.
 */
import { z } from "zod";

// ---- domain types -------------------------------------------------------

export const decodedSignalSchema = z.object({
  name: z.string(),
  value: z.union([z.number(), z.boolean(), z.string(), z.null()]),
  unit: z.string().nullable(),
  channel: z.enum(["A", "B", "unknown"]),
  can_id: z.number().int(),
  at_ms: z.number().int(),
});
export type DecodedSignal = z.infer<typeof decodedSignalSchema>;

export const errqEntrySchema = z.object({
  code: z.number().int(),
  name: z.string().nullable(),
  description: z.string(),
  severity: z.enum(["info", "warn", "error", "critical"]).nullable(),
  channel: z.enum(["A", "B"]),
  byte: z.number().int(),
  bit: z.number().int(),
  first_seen_ms: z.number().int(),
  last_seen_ms: z.number().int(),
});
export type ErrqEntry = z.infer<typeof errqEntrySchema>;

export const errqDisappearedKeySchema = z.object({
  channel: z.enum(["A", "B"]),
  byte: z.number().int(),
  bit: z.number().int(),
});

export const rawFrameSchema = z.object({
  at_ms: z.number().int(),
  can_id: z.number().int(),
  dlc: z.number().int(),
  payload_hex: z.string(),
});
export type RawFrame = z.infer<typeof rawFrameSchema>;

// ---- server -> client envelopes ----------------------------------------

const readyEnvelope = z.object({
  kind: z.literal("ready"),
  payload: z.object({
    session_id: z.string(),
    host_id: z.string(),
    errq_loaded: z.boolean(),
    errq_source_path: z.string().nullable(),
    dbc_loaded: z.boolean(),
    dbc_source_path: z.string().nullable(),
    server_build: z.string().nullable(),
  }),
});

const statusEnvelope = z.object({
  kind: z.literal("status"),
  payload: z.object({
    state: z.enum(["connecting", "connected", "lost", "closed"]),
    reason: z.string().nullable().optional(),
    ssh_stderr_first_line: z.string().nullable().optional(),
    since_ms: z.number().int(),
    pause_buffer_count: z.number().int().default(0),
  }),
});

const signalUpdateEnvelope = z.object({
  kind: z.literal("signal_update"),
  payload: z.object({
    at_ms: z.number().int(),
    signals: z.array(decodedSignalSchema),
  }),
});

const errqUpdateEnvelope = z.object({
  kind: z.literal("errq_update"),
  payload: z.object({
    appeared: z.array(errqEntrySchema).default([]),
    disappeared: z.array(errqDisappearedKeySchema).default([]),
  }),
});

const rawFrameEnvelope = z.object({
  kind: z.literal("raw_frame"),
  payload: rawFrameSchema,
});

const errorEnvelope = z.object({
  kind: z.literal("error"),
  payload: z.object({
    code: z.enum(["dbc_decode_failed", "errq_model_unavailable", "rate_limited"]),
    message: z.string(),
  }),
});

export const serverEnvelopeSchema = z.discriminatedUnion("kind", [
  readyEnvelope,
  statusEnvelope,
  signalUpdateEnvelope,
  errqUpdateEnvelope,
  rawFrameEnvelope,
  errorEnvelope,
]);
export type ServerEnvelope = z.infer<typeof serverEnvelopeSchema>;

/**
 * Parse one inbound message as a server envelope. Returns `null` on
 * any validation failure — callers should count + log and continue
 * (forward-compat per `contracts/websocket.md` §"Unknown `kind`").
 */
export function parseServerEnvelope(data: unknown): ServerEnvelope | null {
  const parsed = serverEnvelopeSchema.safeParse(data);
  return parsed.success ? parsed.data : null;
}

// ---- client -> server envelopes ----------------------------------------

export type ClientEnvelope =
  | { kind: "set_filter"; payload: { signal_name_substring: string } }
  | { kind: "set_channel"; payload: { channel: "A" | "B" | "both" } }
  | { kind: "pause"; payload: Record<string, never> }
  | { kind: "resume"; payload: Record<string, never> }
  | { kind: "clear"; payload: Record<string, never> }
  | { kind: "toggle_raw_frames"; payload: { enabled: boolean } };
