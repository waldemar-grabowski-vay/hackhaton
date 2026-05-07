import { AnimatePresence, motion } from "framer-motion";
import { Wrench, Check, ChevronDown, ChevronUp, Camera, MapPin, X } from "lucide-react";
import { useState } from "react";

import { HarnessDiagram } from "@/components/result/HarnessDiagram";
import { TelestationDiagram } from "@/components/result/TelestationDiagram";

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
import { connectorLocations } from "@/connectorLocations";
import type { DiagnosticItem } from "@/api/schemas";

interface RepairGuideSheetProps {
  item: DiagnosticItem;
  hostType?: "vehicle" | "telestation";
  open: boolean;
  onClose: () => void;
}

export function RepairGuideSheet({ item, hostType, open, onClose }: RepairGuideSheetProps) {
  const developer = useDeveloperMode((s) => s.enabled);
  const guide = guides[item.id];
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [debugOpen, setDebugOpen] = useState(false);
  const [focusedConnector, setFocusedConnector] = useState<string | null>(null);

  function toggleStep(index: number) {
    setCompletedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  function locateConnector(id: string) {
    setFocusedConnector((prev) => (prev === id ? null : id));
  }

  const focusLocation = focusedConnector ? connectorLocations[focusedConnector] : undefined;

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="flex h-[94vh] max-w-[92vw] flex-col gap-0 overflow-hidden p-0">
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

        {/* Two-panel body */}
        <div style={{ flex: 1, minHeight: 0, display: "flex", overflow: "hidden" }}>
          {/* Left panel — repair guide */}
          <div className="flex w-[44%] shrink-0 flex-col overflow-y-auto border-r border-border/30 px-5 py-4">
            <div className="space-y-3">
              {guide ? (
                <>
                  {guide.steps.map((step, i) => {
                    const done = completedSteps.has(i);
                    return (
                      <div
                        key={i}
                        className={cn(
                          "w-full rounded-lg border transition-colors",
                          done
                            ? "border-success/30 bg-success/8"
                            : "border-border/50 bg-card",
                        )}
                      >
                        <button
                          type="button"
                          onClick={() => toggleStep(i)}
                          className="w-full p-3.5 text-left hover:bg-muted/30 rounded-lg transition-colors"
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
                        {step.connectors && step.connectors.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 border-t border-border/20 px-3.5 py-2">
                            {step.connectors.map((c) => (
                              <button
                                key={c.id}
                                type="button"
                                onClick={() => locateConnector(c.id)}
                                className={cn(
                                  "inline-flex items-center gap-1 rounded border px-2 py-1 text-[10px] font-medium transition-colors",
                                  focusedConnector === c.id
                                    ? "border-primary/50 bg-primary/15 text-primary"
                                    : "border-border/50 bg-muted/30 text-muted-foreground hover:border-primary/30 hover:bg-primary/10 hover:text-primary",
                                )}
                              >
                                <MapPin className="h-2.5 w-2.5" />
                                {c.label}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
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
                                  {s.diagram && (
                                    <div
                                      className="mb-2 w-full overflow-x-auto rounded [&>svg]:h-auto [&>svg]:w-full"
                                      // SVG is static bundle content, not user input
                                      dangerouslySetInnerHTML={{ __html: s.diagram }}
                                    />
                                  )}
                                  {s.photos && s.photos.length > 0 && (
                                    <div className="mb-2 flex flex-wrap gap-1.5">
                                      {s.photos.map((photo, pi) => (
                                        <a
                                          key={pi}
                                          href={photo.url}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="inline-flex items-center gap-1 rounded border border-border/50 bg-muted/30 px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:border-primary/40 hover:bg-primary/10 hover:text-primary"
                                        >
                                          <Camera className="h-3 w-3" />
                                          {photo.label}
                                        </a>
                                      ))}
                                    </div>
                                  )}
                                  {s.connectors && s.connectors.length > 0 && (
                                    <div className="mb-2 flex flex-wrap gap-1.5">
                                      {s.connectors.map((c) => (
                                        <button
                                          key={c.id}
                                          type="button"
                                          onClick={() => locateConnector(c.id)}
                                          className={cn(
                                            "inline-flex items-center gap-1 rounded border px-2 py-1 text-[10px] font-medium transition-colors",
                                            focusedConnector === c.id
                                              ? "border-primary/50 bg-primary/15 text-primary"
                                              : "border-border/50 bg-muted/30 text-muted-foreground hover:border-primary/30 hover:bg-primary/10 hover:text-primary",
                                          )}
                                        >
                                          <MapPin className="h-2.5 w-2.5" />
                                          {c.label}
                                        </button>
                                      ))}
                                    </div>
                                  )}
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
          </div>

          {/* Right panel — harness diagram */}
          <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <div className="flex items-center justify-between border-b border-border/30 bg-muted/10 px-3 py-1.5" style={{ flexShrink: 0 }}>
              <span className="text-[11px] font-medium text-muted-foreground">
                {focusedConnector
                  ? `Locating: ${focusedConnector}`
                  : hostType === "telestation" ? "Telestation harness" : "Vehicle diagram"}
              </span>
              {focusedConnector && (
                <button
                  type="button"
                  onClick={() => setFocusedConnector(null)}
                  className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground"
                >
                  <X className="h-3 w-3" />
                  Reset view
                </button>
              )}
            </div>
            <div style={{ flex: 1, minHeight: 0, position: "relative" }}>
              {hostType === "telestation" ? (
                <TelestationDiagram
                  focusTarget={focusedConnector ? { connectorId: focusedConnector } : undefined}
                />
              ) : (
                <HarnessDiagram focusLocation={focusLocation} />
              )}
            </div>
          </div>
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
