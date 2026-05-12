/**
 * UnreachableState (T055).
 *
 * Rendered when `outcome === "unreachable"` or `"timeout"` (FR-006).
 * Shows the failure reason badge (if known) and inline troubleshooting steps.
 * Debug suggestions are gated behind developer mode.
 */
import { useState } from "react";
import { motion } from "framer-motion";
import { CloudOff, TimerOff, ChevronDown, ChevronUp, Check, Terminal } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { strings } from "@/strings";
import { offlineGuides } from "@/guides";
import { useDeveloperMode } from "@/lib/developerMode";
import { cn } from "@/lib/utils";

interface UnreachableStateProps {
  outcome: "unreachable" | "timeout";
  hostLabel: string;
  offlineReason?: string | null;
}

export function UnreachableState({ outcome, hostLabel, offlineReason }: UnreachableStateProps) {
  const Icon = outcome === "timeout" ? TimerOff : CloudOff;
  const copy =
    outcome === "timeout" ? strings.outcomes.timeout : strings.outcomes.unreachable;
  const { enabled: devMode } = useDeveloperMode();
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [openDebug, setOpenDebug] = useState<number | null>(null);

  const guide =
    (offlineReason && offlineGuides[offlineReason]) || offlineGuides.__default!;

  const reasonLabel =
    offlineReason &&
    (strings.outcomes.offlineReasons as Record<string, string>)[offlineReason];

  function toggleStep(i: number) {
    setCompletedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="space-y-4"
    >
      {/* Header card */}
      <Card className="glass-strong">
        <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
          <div className="grid h-14 w-14 place-items-center rounded-full bg-destructive/10 text-destructive ring-1 ring-destructive/30">
            <Icon className="h-6 w-6" />
          </div>
          <div className="space-y-1">
            <div className="text-lg font-semibold">{copy.title}</div>
            <div className="text-sm text-muted-foreground">
              {copy.body} <span className="font-mono">{hostLabel}</span>
            </div>
          </div>
          {reasonLabel && (
            <span className="rounded-full border border-destructive/30 bg-destructive/10 px-3 py-0.5 text-xs font-medium text-destructive">
              {reasonLabel}
            </span>
          )}
        </CardContent>
      </Card>

      {/* Repair steps */}
      <div className="space-y-2">
        <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground px-1">
          Troubleshooting steps
        </div>
        {guide.steps.map((step, i) => {
          const done = completedSteps.has(i);
          return (
            <button
              key={i}
              type="button"
              onClick={() => toggleStep(i)}
              className={cn(
                "w-full rounded-lg border p-3.5 text-left transition-colors",
                done
                  ? "border-success/30 bg-success/8"
                  : "border-border/50 bg-card hover:bg-muted/30",
              )}
            >
              <div className="flex items-start gap-3">
                <div
                  className={cn(
                    "mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full text-[11px] font-bold ring-1 transition-colors",
                    done
                      ? "bg-success/20 text-success ring-success/40"
                      : "bg-muted text-muted-foreground ring-border",
                  )}
                >
                  {done ? <Check className="h-3.5 w-3.5" /> : i + 1}
                </div>
                <div className="min-w-0 flex-1">
                  <div className={cn("text-sm font-medium leading-snug", done && "line-through opacity-60")}>
                    {step.title}
                  </div>
                  {step.body && (
                    <div className="mt-1 whitespace-pre-wrap text-xs text-muted-foreground leading-relaxed">
                      {step.body}
                    </div>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Debug suggestions — developer mode only */}
      {devMode && guide.debugSuggestions.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground px-1">
            Debug
          </div>
          {guide.debugSuggestions.map((s, i) => (
            <div
              key={i}
              className="rounded-lg border border-border/50 bg-card overflow-hidden"
            >
              <button
                type="button"
                onClick={() => setOpenDebug(openDebug === i ? null : i)}
                className="flex w-full items-center justify-between gap-2 p-3 text-left hover:bg-muted/30 transition-colors"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <Terminal className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <span className="text-xs font-medium truncate">{s.label}</span>
                </div>
                {openDebug === i
                  ? <ChevronUp className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  : <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />}
              </button>
              {openDebug === i && (
                <div className="border-t border-border/30 p-3 space-y-2">
                  {s.diagram && (
                    <div
                      className="overflow-x-auto rounded"
                      dangerouslySetInnerHTML={{ __html: s.diagram }}
                    />
                  )}
                  <pre className="whitespace-pre-wrap text-xs text-muted-foreground font-mono leading-relaxed">
                    {s.body}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
