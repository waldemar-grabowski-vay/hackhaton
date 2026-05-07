/**
 * LiveDiagnosticButton (T015 / FR-001).
 *
 * Polls /api/health, renders the "Live diagnostic" entry point only
 * when `live_diagnostic.enabled` is true (Developer mode on). Clicking
 * navigates to /live.
 *
 * The visibility check is server-side authoritative — the on-disk
 * setting is what /api/health reports, so toggling Developer mode in
 * settings.toml and refreshing is enough to make the button appear.
 */
import { useQuery } from "@tanstack/react-query";
import { Activity } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { healthSchema, type Health } from "@/api/schemas";

async function fetchHealth(): Promise<Health> {
  const resp = await fetch("/api/health");
  if (!resp.ok) throw new Error(`health: ${resp.status}`);
  return healthSchema.parse(await resp.json());
}

export function LiveDiagnosticButton() {
  const { data } = useQuery<Health>({
    queryKey: ["health-live"],
    queryFn: fetchHealth,
    staleTime: 30_000,
    retry: false,
  });
  if (!data?.live_diagnostic?.enabled) return null;
  return (
    <Button asChild variant="outline" size="sm">
      <Link to="/live" className="gap-2">
        <Activity className="h-4 w-4" />
        Live diagnostic
      </Link>
    </Button>
  );
}
