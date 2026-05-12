/**
 * Host-versions API client (007).
 *
 * Talks to `GET /api/host/{host_id}/versions`. Each of the three
 * version fields carries a per-field record:
 *   - value: live version string (or null when unavailable)
 *   - verdict: match / drift / no-manifest / unavailable
 *   - expected: manifest's expected value when verdict = drift
 *   - reason: plain-language one-liner when verdict = unavailable
 *   - as_of: timestamp the value was read from the host
 *
 * `?fresh=true` bypasses the server-side 60 s TTL cache and triggers
 * a fresh engine invocation. Pass `{ fresh: true }` to `useHostVersions`
 * to land that query.
 */
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

import { ApiError, apiRequest } from "@/api/client";
import { diagnosticRunSchema, hostSchema } from "@/api/schemas";

export const versionVerdictSchema = z.enum(["match", "drift", "no-manifest", "unavailable"]);
export type VersionVerdict = z.infer<typeof versionVerdictSchema>;

export const versionFieldSchema = z.object({
  value: z.string().nullable(),
  verdict: versionVerdictSchema,
  expected: z.string().nullable(),
  reason: z.string().nullable(),
  as_of: z.string(), // ISO-8601 UTC timestamp; we format it in the page
});
export type VersionField = z.infer<typeof versionFieldSchema>;

export const hostVersionsSchema = z.object({
  vdrive_manifest: versionFieldSchema,
  vreecu_version: versionFieldSchema,
  sec_version: versionFieldSchema,
});
export type HostVersions = z.infer<typeof hostVersionsSchema>;

export const hostVersionsResponseSchema = z.object({
  host: hostSchema,
  versions: hostVersionsSchema,
  // 008: the restored check battery — present when the executor produced
  // a run for this host; null when no run was produced (engine-only mode,
  // run-in-progress, etc.). REECU-owned rows are NOT in here (they live
  // in `versions` instead — FR-011).
  run: diagnosticRunSchema.nullable(),
  source: z.enum(["live", "unavailable"]),
});
export type HostVersionsResponse = z.infer<typeof hostVersionsResponseSchema>;

export interface UseHostVersionsOptions {
  /** When true, append `?fresh=true` so the backend bypasses its TTL cache. */
  fresh?: boolean;
}

export function useHostVersions(
  hostId: string | undefined,
  options: UseHostVersionsOptions = {},
) {
  const fresh = Boolean(options.fresh);
  return useQuery<HostVersionsResponse, ApiError>({
    // Distinct cache keys for fresh vs cached fetches so React Query treats
    // them as independent inflights — clicking refresh re-renders the
    // loading state on every cell instead of silently reusing prior data.
    queryKey: ["host-versions", hostId, { fresh }],
    enabled: Boolean(hostId),
    retry: false,
    queryFn: () =>
      apiRequest({
        method: "GET",
        path: `/api/host/${encodeURIComponent(hostId!)}/versions${
          fresh ? "?fresh=true" : ""
        }`,
        responseSchema: hostVersionsResponseSchema,
      }),
  });
}
