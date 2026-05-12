/**
 * LiveDiagnosticButton — TS_diag entry point.
 *
 * Renders the "Live diagnostic" entry point when Developer mode is on
 * (read from the localStorage-backed `useDeveloperMode` store — the
 * UI toggle is the source of truth). The `/api/health` flag is no
 * longer the gate (it was indirectly driven by the backend's
 * `settings.developer_mode` which the UI never updates); the /live
 * page itself owns its own readiness UI for missing errq/DBC files.
 *
 * Two visual variants:
 *  - "header" (default): outline + small — sits among other header
 *    chrome (EngineModeBadge, Developer-mode switch).
 *  - "main": primary-style + large — sits next to the picker's
 *    Continue button on the main page (FR-001, FR-013).
 */
import { Activity } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useDeveloperMode } from "@/lib/developerMode";

export interface LiveDiagnosticButtonProps {
  variant?: "header" | "main";
}

export function LiveDiagnosticButton({ variant = "header" }: LiveDiagnosticButtonProps) {
  const enabled = useDeveloperMode((s) => s.enabled);
  if (!enabled) return null;

  if (variant === "main") {
    return (
      <Button
        asChild
        size="lg"
        variant="outline"
        className="gap-2 border-primary/40 bg-card/60 text-foreground hover:bg-card"
      >
        <Link to="/live">
          <Activity className="h-4 w-4" />
          Live diagnostic
        </Link>
      </Button>
    );
  }

  return (
    <Button asChild variant="outline" size="sm">
      <Link to="/live" className="gap-2">
        <Activity className="h-4 w-4" />
        Live diagnostic
      </Link>
    </Button>
  );
}
