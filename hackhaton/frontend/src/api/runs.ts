/**
 * Runs API hook (T040).
 *
 * v1 exposes a single hook: `useRunCheck(hostId)` triggers POST /api/runs.
 * Per FR-028 + research R7, there is no `useLatestRun` / `GET /api/runs/latest`
 * — the result view is blank-on-entry and never auto-displays a stored
 * prior run. Backend persistence (FR-026) is server-side audit only in v1.
 *
 * 409 responses surface a toast (FR-011); 503 / inventory-empty responses
 * are handled higher up by the inventory query branch.
 */
import { useMutation } from "@tanstack/react-query";

import { ApiError, apiRequest } from "@/api/client";
import { DiagnosticRun, diagnosticRunSchema } from "@/api/schemas";
import { useToast } from "@/lib/hooks/use-toast";
import { strings } from "@/strings";

export function useRunCheck(hostId: string | undefined) {
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
