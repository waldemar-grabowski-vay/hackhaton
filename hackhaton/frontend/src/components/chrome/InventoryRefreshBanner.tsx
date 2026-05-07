/**
 * InventoryRefreshBanner (T080, FR-027).
 *
 * Renders a non-blocking banner once `meta.consecutive_failed_refreshes`
 * crosses the configured threshold (default 3, override via
 * `VITE_REFRESH_FAILURE_THRESHOLD`). Below the threshold the banner is
 * silent — single transient failures are background-only.
 *
 * The banner does NOT block the wizard. The cached inventory continues
 * to drive the picker; the manual "Update inventory" affordance
 * (FR-017) remains available throughout.
 */
import { AlertTriangle } from "lucide-react";

import type { InventoryMeta } from "@/api/schemas";
import { Card, CardContent } from "@/components/ui/card";
import { strings } from "@/strings";

interface InventoryRefreshBannerProps {
  meta: InventoryMeta;
}

function readThreshold(): number {
  const raw = import.meta.env.VITE_REFRESH_FAILURE_THRESHOLD;
  if (typeof raw !== "string") return 3;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) && n > 0 ? n : 3;
}

export function InventoryRefreshBanner({ meta }: InventoryRefreshBannerProps) {
  const threshold = readThreshold();
  const failures = meta.consecutive_failed_refreshes;
  if (failures < threshold) return null;

  return (
    <Card
      role="status"
      data-testid="inventory-refresh-banner"
      className="glass border-amber-500/40 bg-amber-500/5"
    >
      <CardContent className="flex items-start gap-3 p-3 text-sm">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
        <div className="space-y-1">
          <div className="font-semibold">
            {strings.inventory.refreshFailedBanner.title}
          </div>
          <div className="text-muted-foreground">
            {strings.inventory.refreshFailedBanner.body}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
