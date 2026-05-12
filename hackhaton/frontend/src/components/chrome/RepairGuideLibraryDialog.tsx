import { BookOpen, Car, Radio } from "lucide-react";
import { useState } from "react";

import type { CheckCategory, DiagnosticItem } from "@/api/schemas";
import { CategoryBadge } from "@/components/result/CategoryBadge";
import { RepairGuideSheet } from "@/components/result/RepairGuideSheet";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { CATEGORY_ORDER, GUIDE_CATALOG } from "@/guideLibrary";
import { categoryLabel, t } from "@/strings";
import { cn } from "@/lib/utils";

type HostTab = "vehicle" | "telestation";

function syntheticItem(id: string, category: CheckCategory): DiagnosticItem {
  return {
    id,
    name_key: `item.${id}.name`,
    description_key: null,
    category,
    status: "error",
    recommended_action_key: `item.${id}.action`,
    raw_detail: null,
  };
}

interface RepairGuideLibraryDialogProps {
  open: boolean;
  onClose: () => void;
}

export function RepairGuideLibraryDialog({ open, onClose }: RepairGuideLibraryDialogProps) {
  const [tab, setTab] = useState<HostTab>("vehicle");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const entries = GUIDE_CATALOG.filter((e) =>
    tab === "vehicle" ? e.ve : e.ts,
  );

  const byCategory = CATEGORY_ORDER.reduce<Record<CheckCategory, typeof entries>>(
    (acc, cat) => {
      acc[cat] = entries.filter((e) => e.category === cat);
      return acc;
    },
    {} as Record<CheckCategory, typeof entries>,
  );

  const selectedEntry = selectedId
    ? GUIDE_CATALOG.find((e) => e.id === selectedId) ?? null
    : null;

  return (
    <>
      <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
        <DialogContent className="flex h-[80vh] max-w-lg flex-col gap-0 overflow-hidden p-0">
          <DialogHeader className="border-b border-border/50 px-5 py-4">
            <div className="flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-primary" />
              <DialogTitle className="text-base font-semibold">Repair Guide Library</DialogTitle>
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Select a guide to open the step-by-step repair instructions.
            </p>
          </DialogHeader>

          {/* VE / TS toggle */}
          <div className="flex gap-1.5 border-b border-border/40 bg-muted/10 px-4 py-2.5">
            <button
              type="button"
              onClick={() => setTab("vehicle")}
              className={cn(
                "flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-semibold transition-colors",
                tab === "vehicle"
                  ? "border-primary/50 bg-primary/12 text-primary"
                  : "border-border/50 bg-transparent text-muted-foreground hover:bg-muted/40",
              )}
            >
              <Car className="h-3.5 w-3.5" />
              Vehicle (VE)
            </button>
            <button
              type="button"
              onClick={() => setTab("telestation")}
              className={cn(
                "flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-semibold transition-colors",
                tab === "telestation"
                  ? "border-primary/50 bg-primary/12 text-primary"
                  : "border-border/50 bg-transparent text-muted-foreground hover:bg-muted/40",
              )}
            >
              <Radio className="h-3.5 w-3.5" />
              Telestation (TS)
            </button>
          </div>

          {/* Guide list */}
          <div className="flex-1 overflow-y-auto px-4 py-3">
            {CATEGORY_ORDER.map((cat) => {
              const items = byCategory[cat];
              if (!items.length) return null;
              return (
                <div key={cat} className="mb-5">
                  <div className="mb-2 flex items-center gap-2">
                    <CategoryBadge category={cat} />
                    <span className="text-[11px] text-muted-foreground">
                      {categoryLabel(cat)}
                    </span>
                  </div>
                  <div className="space-y-1.5">
                    {items.map((entry) => (
                      <button
                        key={entry.id}
                        type="button"
                        onClick={() => {
                          setSelectedId(entry.id);
                          onClose();
                        }}
                        className="flex w-full items-center justify-between rounded-lg border border-border/50 bg-card px-3.5 py-2.5 text-left transition-colors hover:border-primary/30 hover:bg-primary/5"
                      >
                        <span className="text-sm font-medium">
                          {t(`item.${entry.id}.name`)}
                        </span>
                        <BookOpen className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="border-t border-border/50 px-5 py-3">
            <Button variant="outline" size="sm" className="w-full" onClick={onClose}>
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {selectedEntry && (
        <RepairGuideSheet
          item={syntheticItem(selectedEntry.id, selectedEntry.category)}
          hostType={tab}
          open={selectedId !== null}
          onClose={() => setSelectedId(null)}
        />
      )}
    </>
  );
}
