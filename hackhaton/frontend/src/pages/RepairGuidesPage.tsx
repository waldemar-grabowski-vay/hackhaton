import { BookOpen, Car, Columns2, Maximize2, Radio, Search } from "lucide-react";
import { useState } from "react";

import type { CheckCategory, DiagnosticItem } from "@/api/schemas";
import { CategoryBadge } from "@/components/result/CategoryBadge";
import { HarnessDiagram } from "@/components/result/HarnessDiagram";
import { RepairGuideSheet } from "@/components/result/RepairGuideSheet";
import { TelestationDiagram } from "@/components/result/TelestationDiagram";
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

export function RepairGuidesPage() {
  const [tab, setTab] = useState<HostTab>("vehicle");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [showHarness, setShowHarness] = useState(true);

  const entries = GUIDE_CATALOG.filter((e) => {
    if (tab === "vehicle" ? !e.ve : !e.ts) return false;
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    const name = t(`item.${e.id}.name`).toLowerCase();
    return name.includes(q) || e.id.includes(q) || e.category.includes(q);
  });

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
    // Full-height layout: override the container's vertical padding [top/bottom spacing]
    <div className="-my-10 sm:-my-16 flex h-dvh flex-col">

      {/* Page header bar */}
      <div className="flex shrink-0 items-center justify-between border-b border-border/50 bg-background/80 px-6 py-3 backdrop-blur">
        <div className="flex items-center gap-2.5">
          <BookOpen className="h-4 w-4 text-primary" />
          <span className="text-sm font-semibold">Repair Guide Library</span>
        </div>

        {/* VE / TS toggle + diagram visibility toggle */}
        <div className="flex gap-1.5">
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
          <button
            type="button"
            onClick={() => setShowHarness((v) => !v)}
            className="flex items-center gap-1.5 rounded-md border border-border/50 px-3 py-1.5 text-xs font-semibold text-muted-foreground transition-colors hover:bg-muted/40"
          >
            {showHarness ? <Columns2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
            {showHarness ? "Hide diagram" : "Show diagram"}
          </button>
        </div>
      </div>

      {/* Two-column body [main content area split into two side-by-side panels] */}
      <div className="flex flex-1 overflow-hidden">

        {/* Left panel — guide list */}
        <aside className="flex w-72 shrink-0 flex-col overflow-y-auto border-r border-border/40 bg-muted/5 px-4 py-4">
          {/* Search bar */}
          <div className="relative mb-3">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search guides…"
              className="w-full rounded-md border border-border/50 bg-background/60 py-1.5 pl-8 pr-3 text-xs placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary/40"
            />
          </div>
          <p className="mb-3 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            {tab === "vehicle" ? "Vehicle guides" : "Telestation guides"}
          </p>
          {entries.length === 0 ? (
            <p className="text-xs text-muted-foreground">No guides match "{query}".</p>
          ) : (
            CATEGORY_ORDER.map((cat) => {
              const items = byCategory[cat];
              if (!items.length) return null;
              return (
                <div key={cat} className="mb-5">
                  <div className="mb-2">
                    <CategoryBadge category={cat} />
                  </div>
                  <div className="space-y-1">
                    {items.map((entry) => (
                      <button
                        key={entry.id}
                        type="button"
                        onClick={() => setSelectedId(entry.id)}
                        className={cn(
                          "flex w-full items-center justify-between rounded-lg border px-3 py-2.5 text-left transition-colors hover:border-primary/30 hover:bg-primary/5",
                          selectedId === entry.id
                            ? "border-primary/50 bg-primary/10"
                            : "border-border/40 bg-card",
                        )}
                      >
                        <span className="text-sm font-medium leading-snug">
                          {t(`item.${entry.id}.name`)}
                        </span>
                        <BookOpen className="ml-2 h-3 w-3 shrink-0 text-muted-foreground" />
                      </button>
                    ))}
                  </div>
                </div>
              );
            })
          )}
        </aside>

        {/* Right panel — only rendered when showHarness=true */}
        {showHarness && (
          <div className="relative flex flex-1 flex-col overflow-hidden">
            <div className="flex shrink-0 items-center gap-2 border-b border-border/30 bg-muted/10 px-4 py-1.5">
              <span className="text-[11px] font-medium text-muted-foreground">
                {tab === "vehicle" ? "Vehicle harness" : "Telestation harness"}
              </span>
              <span className="text-[10px] text-muted-foreground/50">
                — click any guide on the left to open step-by-step instructions
              </span>
            </div>
            <div className="relative flex-1 overflow-hidden">
              {tab === "vehicle" ? (
                <HarnessDiagram />
              ) : (
                <TelestationDiagram />
              )}
            </div>
          </div>
        )}
      </div>

      {/* Repair guide sheet [the step-by-step dialog that opens on top of everything] */}
      {selectedEntry && (
        <RepairGuideSheet
          item={syntheticItem(selectedEntry.id, selectedEntry.category)}
          hostType={tab}
          open={selectedId !== null}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}
