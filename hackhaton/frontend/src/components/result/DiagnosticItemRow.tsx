/**
 * DiagnosticItemRow.
 *
 * One row per diagnostic item. Plain-language name, category badge,
 * recommended action paragraph for errors AND warnings. The raw_detail
 * expand control is rendered only when developer mode is ON (FR-022);
 * the data is always in the payload so toggling does not refetch
 * (FR-021).
 *
 * 002 / FR-004a + FR-004b — three-status rendering:
 *   working — green check, no border tint.
 *   warning — amber AlertTriangle, amber border, amber Next-step pill.
 *   error   — red X, red border, red Next-step pill.
 *
 * Both `error` and `warning` items live under "Needs attention" and
 * carry a `recommended_action_key`; the visual distinction tells the
 * operator which is alarming vs. soft signal.
 */
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  Check,
  X,
  ChevronDown,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { CategoryBadge } from "@/components/result/CategoryBadge";
import { useDeveloperMode } from "@/lib/developerMode";
import { cn } from "@/lib/utils";
import type { DiagnosticItem, ItemStatus } from "@/api/schemas";
import { strings, t } from "@/strings";

interface DiagnosticItemRowProps {
  item: DiagnosticItem;
}

interface StatusVisuals {
  border: string | undefined;
  iconBg: string;
  iconRing: string;
  iconClass: string;
  IconComponent: typeof Check;
  pillBg: string;
  pillRing: string;
  pillLabelClass: string;
}

const STATUS_VISUALS: Record<ItemStatus, StatusVisuals> = {
  working: {
    border: undefined,
    iconBg: "bg-success/15",
    iconRing: "ring-success/30",
    iconClass: "text-success",
    IconComponent: Check,
    pillBg: "bg-success/8",
    pillRing: "ring-success/25",
    pillLabelClass: "text-success",
  },
  warning: {
    border: "border-warning/40",
    iconBg: "bg-warning/15",
    iconRing: "ring-warning/30",
    iconClass: "text-warning",
    IconComponent: AlertTriangle,
    pillBg: "bg-warning/10",
    pillRing: "ring-warning/30",
    pillLabelClass: "text-warning",
  },
  error: {
    border: "border-destructive/40",
    iconBg: "bg-destructive/15",
    iconRing: "ring-destructive/30",
    iconClass: "text-destructive",
    IconComponent: X,
    pillBg: "bg-destructive/10",
    pillRing: "ring-destructive/30",
    pillLabelClass: "text-destructive",
  },
};

export function DiagnosticItemRow({ item }: DiagnosticItemRowProps) {
  const developer = useDeveloperMode((s) => s.enabled);
  const [open, setOpen] = useState(false);
  const visuals = STATUS_VISUALS[item.status];
  const Icon = visuals.IconComponent;
  const showRecommendedAction =
    (item.status === "error" || item.status === "warning") &&
    Boolean(item.recommended_action_key);

  return (
    <Card
      className={cn(
        "glass overflow-hidden p-0 transition-colors",
        visuals.border,
      )}
      data-status={item.status}
    >
      <div className="flex items-start gap-3 p-4">
        <div
          className={cn(
            "mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full ring-1",
            visuals.iconBg,
            visuals.iconClass,
            visuals.iconRing,
          )}
          aria-hidden
        >
          <Icon className="h-3.5 w-3.5" />
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
          {showRecommendedAction && item.recommended_action_key && (
            <div
              className={cn(
                "mt-2 rounded-md p-2.5 text-xs leading-snug ring-1",
                visuals.pillBg,
                visuals.pillRing,
              )}
            >
              <span className={cn("font-semibold", visuals.pillLabelClass)}>
                Next step:
              </span>{" "}
              <span className="text-foreground/85">
                {t(item.recommended_action_key)}
              </span>
            </div>
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
