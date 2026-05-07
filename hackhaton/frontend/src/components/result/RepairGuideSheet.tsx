/**
 * RepairGuideSheet — step-by-step repair guide for a failing diagnostic item.
 *
 * Operator view: plain-language numbered steps, physical-action indicator,
 * per-step completion tracking (session-local, not persisted — spec assumption 3).
 * Developer view: adds "Debug suggestions" section with harness signal paths,
 * connector references, and shell commands (FR-006 / FR-007).
 */
import { AnimatePresence, motion } from "framer-motion";
import { Wrench, Check, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { CategoryBadge } from "@/components/result/CategoryBadge";
import { useDeveloperMode } from "@/lib/developerMode";
import { cn } from "@/lib/utils";
import { strings, t } from "@/strings";
import { guides } from "@/guides";
import type { DiagnosticItem } from "@/api/schemas";

interface RepairGuideSheetProps {
  item: DiagnosticItem;
  open: boolean;
  onClose: () => void;
}

export function RepairGuideSheet({ item, open, onClose }: RepairGuideSheetProps) {
  const developer = useDeveloperMode((s) => s.enabled);
  const guide = guides[item.id];
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [debugOpen, setDebugOpen] = useState(false);

  function toggleStep(index: number) {
    setCompletedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="flex max-h-[85vh] max-w-lg flex-col gap-0 overflow-hidden p-0">
        {/* Header */}
        <DialogHeader className="border-b border-border/50 px-5 py-4">
          <div className="flex items-center gap-2">
            <DialogTitle className="text-base font-semibold">
              {t(item.name_key)}
            </DialogTitle>
            <CategoryBadge category={item.category} />
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {guide
              ? `${guide.steps.length} ${guide.steps.length === 1 ? "step" : "steps"}`
              : strings.guide.noGuideTitle}
          </p>
        </DialogHeader>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {guide ? (
            <>
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
                      {/* Step number / checkmark */}
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
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                          <span className={cn("text-sm font-semibold", done && "line-through text-muted-foreground")}>
                            {step.title}
                          </span>
                          {step.physical && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-warning/10 px-2 py-0.5 text-[10px] font-medium text-warning ring-1 ring-warning/25">
                              <Wrench className="h-2.5 w-2.5" />
                              {strings.guide.stepPhysical}
                            </span>
                          )}
                        </div>
                        <p className={cn("mt-1 text-xs leading-relaxed text-muted-foreground", done && "opacity-60")}>
                          {step.body}
                        </p>
                      </div>
                    </div>
                  </button>
                );
              })}

              {/* Developer debug suggestions */}
              {developer && guide.debugSuggestions.length > 0 && (
                <div className="mt-2">
                  <button
                    type="button"
                    onClick={() => setDebugOpen((o) => !o)}
                    className="flex w-full items-center justify-between rounded-md border border-border/40 bg-muted/20 px-3 py-2 text-xs font-medium text-muted-foreground hover:bg-muted/40"
                  >
                    <span>{strings.guide.debugHeading}</span>
                    {debugOpen
                      ? <ChevronUp className="h-3.5 w-3.5" />
                      : <ChevronDown className="h-3.5 w-3.5" />}
                  </button>
                  <AnimatePresence initial={false}>
                    {debugOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                        className="overflow-hidden"
                      >
                        <div className="mt-2 space-y-2">
                          {guide.debugSuggestions.map((s, i) => (
                            <div
                              key={i}
                              className="rounded-md border border-border/40 bg-background/60 p-3"
                            >
                              <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                                {s.label}
                              </div>
                              <pre className="whitespace-pre-wrap break-words font-mono text-[11px] leading-snug text-muted-foreground">
                                {s.body}
                              </pre>
                            </div>
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )}
            </>
          ) : (
            /* No guide available */
            <div className="rounded-lg border border-border/50 bg-muted/20 p-4 text-center">
              <p className="text-sm font-semibold">{strings.guide.noGuideTitle}</p>
              <p className="mt-1 text-xs text-muted-foreground">{strings.guide.noGuideBody}</p>
              {item.recommended_action_key && (
                <div className="mt-3 rounded-md bg-warning/8 p-2.5 text-left text-xs text-warning-foreground/95 ring-1 ring-warning/25">
                  <span className="font-semibold text-warning">Next step: </span>
                  {t(item.recommended_action_key)}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-border/50 px-5 py-3">
          <Button variant="outline" size="sm" className="w-full" onClick={onClose}>
            {strings.guide.closeButton}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
