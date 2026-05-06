/**
 * ResultHero (T052 + T064).
 *
 * Glass card at the top of the result page: host display name, run timestamp,
 * status donut, pass/fail headline. Sized so the headline + host + timestamp
 * stay above the fold on a 360 px viewport (FR-007 / FR-012 / SC-007).
 */
import { motion } from "framer-motion";
import { Sparkles, ShieldAlert } from "lucide-react";

import { StatusDonut } from "@/components/charts/StatusDonut";
import { Card, CardContent } from "@/components/ui/card";
import { strings, prettyHostName } from "@/strings";
import type { Host } from "@/api/schemas";

interface ResultHeroProps {
  host: Host;
  startedAt: string;
  completedAt: string;
  workingCount: number;
  needsAttentionCount: number;
}

function formatRelative(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  if (diffMs < 60_000) return strings.result.timestampJustNow;
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.floor(hours / 24);
  return `${days} d ago`;
}

function formatAbsolute(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function ResultHero({
  host,
  startedAt,
  completedAt: _completedAt,
  workingCount,
  needsAttentionCount,
}: ResultHeroProps) {
  const allHealthy = needsAttentionCount === 0 && workingCount > 0;
  const headline = allHealthy
    ? strings.outcomes.complete.headline
    : strings.outcomes.completeWithErrors.headline;
  const subline = allHealthy
    ? strings.outcomes.complete.subline
    : strings.outcomes.completeWithErrors.subline;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
    >
      <Card className="glass-strong relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            background: allHealthy
              ? "radial-gradient(ellipse at 30% -20%, hsl(var(--success) / 0.18), transparent 55%)"
              : "radial-gradient(ellipse at 30% -20%, hsl(var(--warning) / 0.16), transparent 55%)",
          }}
        />
        <CardContent className="relative flex flex-col gap-6 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
          <div className="min-w-0 space-y-3">
            <div className="flex items-center gap-2">
              {allHealthy ? (
                <Sparkles className="h-4 w-4 text-success" />
              ) : (
                <ShieldAlert className="h-4 w-4 text-warning" />
              )}
              <span
                className={
                  allHealthy
                    ? "text-xs font-medium uppercase tracking-wider text-success/90"
                    : "text-xs font-medium uppercase tracking-wider text-warning/90"
                }
              >
                {headline}
              </span>
            </div>
            <h1 className="truncate text-3xl font-semibold tracking-tight sm:text-4xl">
              <span className="gradient-text">
                {prettyHostName(host.display_name, host.type)}
              </span>
            </h1>
            <p className="text-sm text-muted-foreground">{subline}</p>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 pt-1 text-xs text-muted-foreground">
              <span>
                <span className="font-medium text-foreground">
                  {strings.result.timestampPrefix}
                </span>{" "}
                {formatRelative(startedAt)}
              </span>
              <span aria-hidden>·</span>
              <span className="font-mono">{formatAbsolute(startedAt)}</span>
              <span aria-hidden>·</span>
              <span className="font-mono">{host.id}</span>
            </div>
          </div>
          <div className="shrink-0 self-center sm:self-auto">
            <StatusDonut
              working={workingCount}
              needsAttention={needsAttentionCount}
            />
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
