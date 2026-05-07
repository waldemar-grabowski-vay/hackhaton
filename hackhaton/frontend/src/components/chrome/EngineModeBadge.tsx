/**
 * EngineModeBadge.
 *
 * 002 / FR-007 visibility rule — the operator must always be able to
 * tell whether the SPA is running real diagnostics or fixture data so
 * a fixture-mode demo is never mistaken for a live run.
 *
 * Polls `/api/health` once on mount; renders a small pill in the app
 * header. Live = green; fixture = amber. Engine-unavailable /
 * incompatible = red, with a tooltip.
 */
import { useQuery } from "@tanstack/react-query";
import { CircleCheck, CircleSlash, FlaskConical } from "lucide-react";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface EngineHealth {
  status: string;
  version: string;
  engine_mode: "live" | "fixture" | "engine_unavailable" | "engine_incompatible" | "unknown";
  engine_version: string | null;
}

async function fetchHealth(): Promise<EngineHealth> {
  const resp = await fetch("/api/health");
  if (!resp.ok) throw new Error(`health: ${resp.status}`);
  return (await resp.json()) as EngineHealth;
}

export function EngineModeBadge() {
  const { data } = useQuery<EngineHealth>({
    queryKey: ["engine-health"],
    queryFn: fetchHealth,
    staleTime: 30_000,
    retry: false,
  });
  if (!data) return null;

  const visuals = describe(data.engine_mode);
  const tooltip = data.engine_version
    ? `${visuals.tooltip} · ${data.engine_version}`
    : visuals.tooltip;

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            data-engine-mode={data.engine_mode}
            className={cn(
              "flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium uppercase tracking-wider",
              visuals.classes,
            )}
          >
            <visuals.Icon className="h-3 w-3" />
            {visuals.label}
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom">{tooltip}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function describe(mode: EngineHealth["engine_mode"]): {
  label: string;
  classes: string;
  Icon: typeof CircleCheck;
  tooltip: string;
} {
  switch (mode) {
    case "live":
      return {
        label: "Live",
        classes: "border-success/40 bg-success/10 text-success",
        Icon: CircleCheck,
        tooltip: "Running against real testbeds via ree-debug-cli",
      };
    case "fixture":
      return {
        label: "Fixture",
        classes: "border-warning/40 bg-warning/10 text-warning",
        Icon: FlaskConical,
        tooltip: "Demo / CI mode — running canned fixtures, not real testbeds",
      };
    case "engine_unavailable":
      return {
        label: "Engine missing",
        classes: "border-destructive/40 bg-destructive/10 text-destructive",
        Icon: CircleSlash,
        tooltip: "ree-debug-cli not built. Run `cargo build --release --workspace` from engine/",
      };
    case "engine_incompatible":
      return {
        label: "Engine stale",
        classes: "border-destructive/40 bg-destructive/10 text-destructive",
        Icon: CircleSlash,
        tooltip: "ree-debug-cli built from a SHA the backend doesn't recognise. Rebuild the engine.",
      };
    default:
      return {
        label: "Unknown",
        classes: "border-border/60 bg-card/40 text-muted-foreground",
        Icon: CircleSlash,
        tooltip: "Backend hasn't reported an engine mode yet",
      };
  }
}
