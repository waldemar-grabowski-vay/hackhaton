import { Activity, BookOpen } from "lucide-react";
import { Link } from "react-router-dom";

import { EngineModeBadge } from "@/components/chrome/EngineModeBadge";
import { LiveDiagnosticButton } from "@/components/chrome/LiveDiagnosticButton";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useDeveloperMode } from "@/lib/developerMode";
import { strings } from "@/strings";

export function AppHeader() {
  const enabled = useDeveloperMode((s) => s.enabled);
  const toggle = useDeveloperMode((s) => s.toggle);

  return (
    <header className="sticky top-0 z-30 border-b border-border/60 bg-background/80 backdrop-blur-xl">
      <div className="container flex h-14 items-center justify-between gap-4">
        {/* Logo doubles as the "Home" link — clicking it from anywhere
            (Live diagnostic, run result, etc.) returns to the picker. */}
        <Link
          to="/"
          className="flex items-center gap-2.5 rounded-md transition-opacity hover:opacity-90"
          aria-label="VayOBD home"
        >
          <div className="grid h-8 w-8 place-items-center rounded-md bg-primary/15 text-primary ring-1 ring-primary/30">
            <Activity className="h-4 w-4" />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold tracking-tight">
              <span className="gradient-text">{strings.app.name}</span>
            </div>
            <div className="text-[11px] text-muted-foreground">
              {strings.app.tagline}
            </div>
          </div>
        </Link>

        <div className="flex items-center gap-3">
          {/* 008 / US5 / FR-017: top-level repair-guide library entry point.
              Operator-facing knowledge — NOT Developer-mode-gated. */}
          <Button asChild variant="outline" size="sm">
            <Link to="/repair-guides" className="gap-2">
              <BookOpen className="h-4 w-4" />
              Repair guides
            </Link>
          </Button>
          <LiveDiagnosticButton />
          <EngineModeBadge />
          <TooltipProvider delayDuration={200}>
            <Tooltip>
              <TooltipTrigger asChild>
                <label className="flex cursor-pointer items-center gap-2 rounded-full border border-border/60 bg-card/40 px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-card/60">
                  <span className="font-medium">Developer mode</span>
                  <Switch
                    checked={enabled}
                    onCheckedChange={toggle}
                    aria-label="Toggle Developer mode"
                  />
                </label>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                {enabled
                  ? "Showing raw output per item"
                  : "Operator view — no raw output"}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>
    </header>
  );
}
