/**
 * StalenessBanner (spec 006 / FR-008 / FR-010 / US3).
 *
 * Renders above the inventory list when:
 *   - any required repo is older than REFRESH_STALENESS_THRESHOLD_SECONDS, OR
 *   - the last refresh ended in a non-success state.
 *
 * Includes a "Refresh now" button that drives the same backend code path as
 * `vayobd refresh` on the CLI (single source of truth).
 */
import { RefreshCw, AlertTriangle } from "lucide-react";

import {
  REFRESH_STALENESS_THRESHOLD_SECONDS,
  useRefreshStatus,
  useTriggerRefresh,
} from "@/api/refresh";
import { Button } from "@/components/ui/button";

function formatRelative(seconds: number | null): string {
  if (seconds === null) return "never";
  if (seconds < 60) return "moments ago";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

export function StalenessBanner() {
  const status = useRefreshStatus();
  const trigger = useTriggerRefresh();

  // Hide on initial load / hard failure. The picker page already has its own
  // empty/error states; the banner is a non-blocking heads-up.
  if (!status.data) return null;

  const data = status.data;
  const stale =
    (data.stalest_age_seconds ?? 0) >= REFRESH_STALENESS_THRESHOLD_SECONDS;
  const lastFailed =
    data.state === "idle" &&
    data.last_refresh_outcome != null &&
    data.last_refresh_outcome !== undefined;
  const running = data.state === "running";

  if (!stale && !lastFailed && !running) return null;

  const onClick = () => {
    if (!trigger.isPending && !running) trigger.mutate();
  };

  const credentialFailure =
    trigger.error?.code === "credentials_failed" ||
    data.last_refresh_outcome === "credentials_failed";

  return (
    <div
      role="status"
      className="mb-4 flex items-start justify-between gap-4 rounded-lg border border-amber-300 bg-amber-50 p-4 text-amber-900"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
        <div>
          <p className="font-medium">
            {credentialFailure
              ? "Your GitHub credentials aren't working anymore."
              : running
                ? "Refreshing repositories…"
                : "Your local copy of the host list is out of date."}
          </p>
          <p className="text-sm">
            {running
              ? "Hang tight — this usually takes under a minute."
              : credentialFailure
                ? "Run `gh auth login` or check your SSH key, then refresh again."
                : `Last sync: ${formatRelative(data.stalest_age_seconds)}.`}
          </p>
        </div>
      </div>
      <Button
        type="button"
        size="sm"
        variant="outline"
        onClick={onClick}
        disabled={running || trigger.isPending}
        className="shrink-0"
      >
        <RefreshCw
          className={`mr-2 h-4 w-4 ${running || trigger.isPending ? "animate-spin" : ""}`}
          aria-hidden
        />
        {running || trigger.isPending ? "Refreshing…" : "Refresh now"}
      </Button>
    </div>
  );
}
