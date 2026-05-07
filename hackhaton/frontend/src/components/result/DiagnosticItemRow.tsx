/**
 * DiagnosticItemRow (T054 + T066).
 *
 * One row per diagnostic item. Plain-language name, category badge,
 * recommended action paragraph for errors. The raw_detail expand control is
 * rendered only when developer mode is ON (FR-022); the data is always in the
 * payload so toggling does not refetch (FR-021).
 */
import { AnimatePresence, motion } from "framer-motion";
import {
  Check,
  X,
  ChevronDown,
  BookOpen,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { CategoryBadge } from "@/components/result/CategoryBadge";
import { RepairGuideSheet } from "@/components/result/RepairGuideSheet";
import { useDeveloperMode } from "@/lib/developerMode";
import { cn } from "@/lib/utils";
import type { DiagnosticItem } from "@/api/schemas";
import { strings, t } from "@/strings";

interface DiagnosticItemRowProps {
  item: DiagnosticItem;
  hostType?: "vehicle" | "telestation";
}

export function DiagnosticItemRow({ item, hostType }: DiagnosticItemRowProps) {
  const developer = useDeveloperMode((s) => s.enabled);
  const [open, setOpen] = useState(false);
  const [guideOpen, setGuideOpen] = useState(false);
  const isError = item.status === "error";

  return (
    <Card
      className={cn(
        "glass overflow-hidden p-0 transition-colors",
        isError && "border-warning/30",
      )}
    >
      <div className="flex items-start gap-3 p-4">
        <div
          className={cn(
            "mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full ring-1",
            isError
              ? "bg-warning/15 text-warning ring-warning/30"
              : "bg-success/15 text-success ring-success/30",
          )}
          aria-hidden
        >
          {isError ? <X className="h-3.5 w-3.5" /> : <Check className="h-3.5 w-3.5" />}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <div className="text-sm font-semibold">{t(item.name_key)}</div>
            <CategoryBadge category={item.category} />
          </div>
          {item.description_key && (
            <p className="mt-1 text-xs text-muted-foreground">
              {t(item.description_key)}
            </p>
          )}
          {isError && item.recommended_action_key && (
            <div className="mt-2 rounded-md bg-warning/8 p-2.5 text-xs leading-snug text-warning-foreground/95 ring-1 ring-warning/25">
              <span className="font-semibold text-warning">Next step:</span>{" "}
              <span className="text-foreground/85">
                {t(item.recommended_action_key)}
              </span>
            </div>
          )}
          {isError && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => setGuideOpen(true)}
              className="mt-2 h-7 gap-1.5 text-xs"
            >
              <BookOpen className="h-3.5 w-3.5" />
              {strings.guide.viewButton}
            </Button>
          )}
          {isError && (
            <RepairGuideSheet
              item={item}
              hostType={hostType}
              open={guideOpen}
              onClose={() => setGuideOpen(false)}
            />
          )}
        </div>
        {developer && (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            className="h-7 shrink-0 gap-1 text-[11px]"
          >
            <ChevronDown
              className={cn(
                "h-3.5 w-3.5 transition-transform",
                open && "rotate-180",
              )}
            />
            {open ? strings.result.rawDetailToggleHide : strings.result.rawDetailToggleShow}
          </Button>
        )}
      </div>
      <AnimatePresence initial={false}>
        {developer && open && (
          <motion.div
            key="raw"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <div className="border-t border-border/50 bg-background/40 px-4 py-3">
              <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                {strings.result.rawDetailLabel}
              </div>
              <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-[11px] leading-snug text-muted-foreground">
                {item.raw_detail ?? strings.result.rawDetailEmpty}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
