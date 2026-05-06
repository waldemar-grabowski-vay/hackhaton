/**
 * ResultGroup (T053).
 *
 * Container for the Working / Needs attention groups on the result page.
 */
import { CheckCircle2, AlertCircle } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface ResultGroupProps {
  variant: "working" | "needs-attention";
  title: string;
  count: number;
  children: ReactNode;
  empty?: ReactNode;
}

export function ResultGroup({
  variant,
  title,
  count,
  children,
  empty,
}: ResultGroupProps) {
  const isWorking = variant === "working";
  const Icon = isWorking ? CheckCircle2 : AlertCircle;
  return (
    <section className="space-y-3">
      <header className="flex items-center gap-2.5">
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
        <div className="flex flex-1 items-baseline gap-2">
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
      </header>
      {count === 0 && empty ? (
        <div className="rounded-xl border border-dashed border-border/60 p-4 text-center text-xs text-muted-foreground">
          {empty}
        </div>
      ) : (
        <div className="space-y-2">{children}</div>
      )}
    </section>
  );
}
