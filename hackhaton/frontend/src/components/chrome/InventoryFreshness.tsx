/**
 * InventoryFreshness (T049).
 *
 * Inline freshness indicator + Update button (FR-018). Shown above the wizard
 * so the operator can see how stale the host list is and trigger an on-demand
 * refresh.
 */
import { RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useRefreshInventory } from "@/api/inventory";
import type { InventoryMeta } from "@/api/schemas";
import { strings } from "@/strings";

interface InventoryFreshnessProps {
  meta: InventoryMeta;
}

function formatRelative(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  if (diffMs < 60_000) return "just now";
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.floor(hours / 24);
  return `${days} d ago`;
}

export function InventoryFreshness({ meta }: InventoryFreshnessProps) {
  const refresh = useRefreshInventory();
  const relative = formatRelative(meta.last_refreshed_at);
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-full border border-border/50 bg-card/30 px-3 py-1.5 text-xs text-muted-foreground">
      <span>
        <span className="font-medium text-foreground">
          {strings.inventory.lastRefreshedPrefix}
        </span>{" "}
        {relative}
        <span className="hidden sm:inline">
          {" · "}
          <span className="font-mono">{meta.source_revision.slice(0, 7)}</span>
          {" · "}
          {meta.host_count} hosts
        </span>
      </span>
      <Button
        size="sm"
        variant="ghost"
        onClick={() => refresh.mutate()}
        disabled={refresh.isPending}
        className="h-6 gap-1.5 px-2 text-xs"
      >
        <RefreshCw
          className={refresh.isPending ? "h-3 w-3 animate-spin" : "h-3 w-3"}
        />
        {refresh.isPending
          ? strings.inventory.refreshing
          : strings.inventory.refreshButton}
      </Button>
    </div>
  );
}
