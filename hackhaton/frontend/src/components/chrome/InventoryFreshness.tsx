/**
 * InventoryFreshness — slim chrome above the wizard.
 *
 * 002 / FR-013a: the cache + refresh button + last-refreshed timestamp
 * from 001 are gone (no more cache to be fresh against). The
 * operator's `git pull` + browser tab refresh is the v1 update flow.
 *
 * Phase 5 / US3 will add an "Inventory location" affordance next to
 * this component for changing the saved path.
 */
import type { InventoryMeta } from "@/api/schemas";

interface InventoryFreshnessProps {
  meta: InventoryMeta;
}

export function InventoryFreshness({ meta }: InventoryFreshnessProps) {
  return (
    <div className="rounded-full border border-border/50 bg-card/30 px-3 py-1.5 text-xs text-muted-foreground">
      {meta.host_count} hosts
    </div>
  );
}
