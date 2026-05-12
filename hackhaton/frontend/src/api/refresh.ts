/**
 * Refresh API client (spec 006 / FR-008 / US3).
 *
 * Talks to `POST /api/refresh` and `GET /api/refresh/status` per
 * specs/006-deb-package-distribution/contracts/http-api.md.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import { ApiError, apiRequest } from "@/api/client";

export const refreshStatusRepoSchema = z.object({
  id: z.string(),
  last_synced_at: z.string().nullable(),
  last_outcome: z.string(),
  resolved_revision: z.string().nullable(),
});

export const refreshStatusSchema = z.object({
  state: z.enum(["idle", "running"]),
  stalest_age_seconds: z.number().nullable(),
  repos: z.array(refreshStatusRepoSchema),
  refresh_id: z.string().optional(),
  started_at: z.string().optional(),
  current_repo: z.string().nullable().optional(),
  completed: z.array(z.string()).optional(),
  last_refresh_outcome: z
    .enum(["partial_failure", "credentials_failed", "network_error", "conflict"])
    .nullable()
    .optional(),
  last_refresh_at: z.string().nullable().optional(),
});

export type RefreshStatus = z.infer<typeof refreshStatusSchema>;

const refreshAcceptedSchema = z.object({
  refresh_id: z.string(),
  started_at: z.string(),
});

const REFRESH_STATUS_KEY = ["refresh", "status"] as const;

export function useRefreshStatus(pollWhileRunning = true) {
  return useQuery<RefreshStatus, ApiError>({
    queryKey: REFRESH_STATUS_KEY,
    queryFn: () =>
      apiRequest({
        method: "GET",
        path: "/api/refresh/status",
        responseSchema: refreshStatusSchema,
      }),
    refetchInterval: (query) => {
      if (!pollWhileRunning) return false;
      return query.state.data?.state === "running" ? 1_000 : false;
    },
    refetchOnWindowFocus: false,
    staleTime: 5_000,
  });
}

export function useTriggerRefresh() {
  const queryClient = useQueryClient();
  return useMutation<{ refresh_id: string; started_at: string }, ApiError, void>({
    mutationFn: () =>
      apiRequest({
        method: "POST",
        path: "/api/refresh",
        body: {},
        responseSchema: refreshAcceptedSchema,
      }),
    onSuccess: async () => {
      // Force-refresh the status query immediately so the banner flips to
      // "running" in the UI without waiting for the next 1 s tick.
      await queryClient.invalidateQueries({ queryKey: REFRESH_STATUS_KEY });
    },
  });
}

/** Stale-bar threshold (seconds). FR-010 — surface staleness. */
export const REFRESH_STALENESS_THRESHOLD_SECONDS = 24 * 60 * 60;
