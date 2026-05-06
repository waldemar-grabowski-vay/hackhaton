/**
 * Runs API hooks (T040).
 *
 * `useRunCheck(hostId)` triggers a POST /api/runs and stores the latest run in
 * the query cache so the result page can read it without a refetch.
 *
 * `useLatestRun(hostId)` reads the persisted last run via GET /api/runs/latest.
 *
 * 409 responses surface a toast (FR-011); 503 / inventory-empty responses are
 * handled higher up by the inventory query branch.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiRequest } from "@/api/client";
import { DiagnosticRun, diagnosticRunSchema } from "@/api/schemas";
import { useToast } from "@/lib/hooks/use-toast";
import { strings } from "@/strings";

export const latestRunQueryKey = (hostId: string) => ["runs", hostId, "latest"] as const;

export function useRunCheck(hostId: string | undefined) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation<DiagnosticRun, ApiError>({
    mutationFn: () => {
      if (!hostId) throw new Error("host_id is required to run a check");
      return apiRequest({
        method: "POST",
        path: "/api/runs",
        body: { host_id: hostId },
        responseSchema: diagnosticRunSchema,
      });
    },
    onSuccess: (run) => {
      if (!hostId) return;
      queryClient.setQueryData(latestRunQueryKey(hostId), run);
    },
    onError: (err) => {
      if (err instanceof ApiError && err.code === "run_in_progress") {
        toast({
          title: strings.runs.inProgressToastTitle,
          description: strings.runs.inProgressToastBody,
        });
        return;
      }
      // Unknown / network — let the page render an inline failure state.
    },
  });
}

export function useLatestRun(hostId: string | undefined) {
  return useQuery<DiagnosticRun | null, ApiError>({
    queryKey: hostId ? latestRunQueryKey(hostId) : ["runs", "noop"],
    queryFn: async () => {
      if (!hostId) return null;
      try {
        return await apiRequest({
          method: "GET",
          path: `/api/runs/latest?host_id=${encodeURIComponent(hostId)}`,
          responseSchema: diagnosticRunSchema,
        });
      } catch (err) {
        if (err instanceof ApiError && err.code === "no_run_yet") return null;
        throw err;
      }
    },
    enabled: Boolean(hostId),
    retry: false,
    staleTime: 0,
  });
}
