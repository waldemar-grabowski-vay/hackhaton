/**
 * ResultGroup (T053).
 *
 * Container for the Working / Needs attention groups on the result page.
 * Optionally collapsible (used to keep the long "Working" list folded by
 * default so the failing items aren't pushed off-screen).
 */
import { CheckCircle2, AlertCircle, ChevronDown } from "lucide-react";
import { useState, type ReactNode } from "react";

import { cn } from "@/lib/utils";

interface ResultGroupProps {
  variant: "working" | "needs-attention";
  title: string;
  count: number;
  children: ReactNode;
  empty?: ReactNode;
  /** When true, the body collapses behind a click on the header. Default: false. */
  collapsible?: boolean;
  /** When `collapsible` is true, controls the initial expanded state. Default: false. */
  defaultExpanded?: boolean;
}

export function ResultGroup({
  variant,
  title,
  count,
  children,
  empty,
  collapsible = false,
  defaultExpanded = false,
}: ResultGroupProps) {
  const isWorking = variant === "working";
  const Icon = isWorking ? CheckCircle2 : AlertCircle;
  const [expanded, setExpanded] = useState(defaultExpanded);
  const showBody = !collapsible || expanded;

  const HeaderTag: "button" | "header" = collapsible ? "button" : "header";

  return (
    <section className="space-y-3">
      <HeaderTag
        className={cn(
          "flex w-full items-center gap-2.5",
          collapsible &&
            "rounded-md p-1 -ml-1 transition-colors hover:bg-card/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        )}
        {...(collapsible
          ? {
              type: "button" as const,
              onClick: () => setExpanded((v) => !v),
              "aria-expanded": expanded,
            }
          : {})}
      >
        <div
          className={cn(
            "grid h-7 w-7 place-items-center rounded-md ring-1",
            isWorking
              ? "bg-success/15 text-success ring-success/30"
              : "bg-warning/15 text-warning ring-warning/30",
          )}
        >
          <Icon className="h-4 w-4" />
        </div>
        <div className="flex flex-1 items-baseline gap-2 text-left">
          <h3 className="text-base font-semibold tracking-tight">{title}</h3>
          <span
            className={cn(
              "text-xs tabular-nums",
              isWorking ? "text-success/80" : "text-warning/80",
            )}
          >
            {count}
          </span>
        </div>
        {collapsible && (
          <ChevronDown
            className={cn(
              "h-4 w-4 text-muted-foreground transition-transform",
              expanded && "rotate-180",
            )}
            aria-hidden
          />
        )}
      </HeaderTag>
      {showBody &&
        (count === 0 && empty ? (
          <div className="rounded-xl border border-dashed border-border/60 p-4 text-center text-xs text-muted-foreground">
            {empty}
          </div>
        ) : (
          <div className="space-y-2">{children}</div>
        ))}
    </section>
  );
}
