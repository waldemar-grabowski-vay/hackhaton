/**
 * RunResultPage (T057, FR-028 + FR-008 + FR-026 + FR-025).
 *
 * - On mount, renders ONLY the host header and a single "Run check" CTA.
 *   No persisted prior run is auto-displayed (FR-028 / research R7).
 *   `useRunCheck` only fires after the operator clicks the CTA.
 * - Once a run completes, swaps in `ResultHero` + Working / Needs attention
 *   groups. The "Run check again" button (US2 / FR-008) re-runs against
 *   the same host and replaces the in-view result.
 * - Unreachable / timeout outcomes render the dedicated state.
 * - Partial outcomes prepend the partial banner.
 * - 100% pass + opt-in confetti via VITE_FEATURE_CONFETTI=true (T069).
 */
import { ArrowLeft, RotateCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useInventory } from "@/api/inventory";
import { useRunCheck } from "@/api/runs";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DiagnosticItemRow } from "@/components/result/DiagnosticItemRow";
import { ResultGroup } from "@/components/result/ResultGroup";
import { ResultHero } from "@/components/result/ResultHero";
import { PartialRunState } from "@/components/states/PartialRunState";
import { RunningState } from "@/components/states/RunningState";
import { UnreachableState } from "@/components/states/UnreachableState";
import { StaggeredItem, StaggeredList } from "@/components/motion/StaggeredList";
import { ApiError } from "@/api/client";
import { prettyHostName, strings } from "@/strings";

export function RunResultPage() {
  const { hostId } = useParams<{ hostId: string }>();

  const inventory = useInventory();
  const host = useMemo(
    () => inventory.data?.hosts.find((h) => h.id === hostId) ?? null,
    [inventory.data, hostId],
  );

  const runMutation = useRunCheck(hostId);

  if (!hostId) {
    return (
      <div className="mx-auto max-w-xl">
        <Card className="glass">
          <CardContent className="p-6 text-sm text-muted-foreground">
            No host selected. <Link to="/" className="text-primary underline">Pick one</Link>.
          </CardContent>
        </Card>
      </div>
    );
  }

  // Only the in-flight / completed mutation drives the displayed run; FR-028
  // forbids auto-displaying a stored prior run.
  const run = runMutation.data ?? null;

  const hostLabel = host
    ? prettyHostName(host.display_name, host.type)
    : hostId;

  const isRunning = runMutation.isPending;

  // 409 toast surfaces via the hook itself; we just keep the button disabled.
  const showRunFailure =
    runMutation.isError &&
    !(runMutation.error instanceof ApiError && runMutation.error.code === "run_in_progress");

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button asChild variant="ghost" size="sm" className="gap-1.5">
          <Link to="/">
            <ArrowLeft className="h-4 w-4" />
            {strings.result.backToWizard}
          </Link>
        </Button>
        {run && !isRunning && (
          <Button
            onClick={() => runMutation.mutate()}
            disabled={isRunning}
            className="gap-2"
            data-testid="run-again-button"
          >
            <RotateCw className={isRunning ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
            {strings.runs.runAgainButton}
          </Button>
        )}
      </div>

      {isRunning && <RunningState hostLabel={hostLabel} />}

      {!isRunning && !run && (
        // FR-028: blank-on-entry. The result view always opens with a
        // single "Run check" CTA — the operator must explicitly trigger
        // the diagnostic. Backend persistence is server-side audit only
        // (FR-026 / research R7); v1 surfaces no read endpoint.
        <Card className="glass" data-testid="run-cta-card">
          <CardContent className="space-y-3 p-6">
            <div className="text-sm font-semibold">
              {strings.runs.noneYet.title}
            </div>
            <div className="text-sm text-muted-foreground">
              {strings.runs.noneYet.body}
            </div>
            <Button
              onClick={() => runMutation.mutate()}
              className="mt-1"
              data-testid="run-check-button"
            >
              {strings.runs.runButton}
            </Button>
          </CardContent>
        </Card>
      )}

      {!isRunning && run && host && (
        <RenderRun host={host} run={run} hostLabel={hostLabel} />
      )}

      {showRunFailure && (
        <Card className="glass border-destructive/30">
          <CardContent className="p-4 text-sm text-destructive">
            {strings.errors.network}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function RenderRun({
  host,
  run,
  hostLabel,
}: {
  host: import("@/api/schemas").Host;
  run: import("@/api/schemas").DiagnosticRun;
  hostLabel: string;
}) {
  if (run.outcome === "unreachable" || run.outcome === "timeout") {
    return <UnreachableState outcome={run.outcome} hostLabel={hostLabel} />;
  }

  const working = run.items.filter((i) => i.status === "working");
  const needsAttention = run.items.filter((i) => i.status === "error");

  // Confetti is opt-in (T069). Side-effect kept minimal: imported lazily and
  // fired once when the component sees a 100% complete pass.
  const fullPass =
    run.outcome === "complete" && needsAttention.length === 0 && working.length > 0;
  useConfettiOnce(fullPass);

  return (
    <div className="space-y-6">
      <ResultHero
        host={host}
        startedAt={run.started_at}
        completedAt={run.completed_at}
        workingCount={working.length}
        needsAttentionCount={needsAttention.length}
      />
      {run.outcome === "partial" && <PartialRunState />}
      <ResultGroup
        variant="needs-attention"
        title={strings.result.needsAttentionHeading}
        count={needsAttention.length}
        empty="Nothing needs attention. Nice."
      >
        <StaggeredList className="space-y-2">
          {needsAttention.map((item) => (
            <StaggeredItem key={item.id}>
              <DiagnosticItemRow item={item} hostType={host.type} />
            </StaggeredItem>
          ))}
        </StaggeredList>
      </ResultGroup>
      <ResultGroup
        variant="working"
        title={strings.result.workingHeading}
        count={working.length}
        empty="No items reported healthy this run."
      >
        <StaggeredList className="space-y-2">
          {working.map((item) => (
            <StaggeredItem key={item.id}>
              <DiagnosticItemRow item={item} hostType={host.type} />
            </StaggeredItem>
          ))}
        </StaggeredList>
      </ResultGroup>
    </div>
  );
}

function useConfettiOnce(fire: boolean) {
  const [done, setDone] = useState(false);
  useEffect(() => {
    if (!fire || done) return;
    if (import.meta.env.VITE_FEATURE_CONFETTI !== "true") return;
    setDone(true);
    // Tiny inline confetti — no extra dep. Fires once per page mount.
    const colors = [
      "hsl(196 100% 56%)",
      "hsl(150 70% 55%)",
      "hsl(38 95% 60%)",
    ];
    const root = document.createElement("div");
    Object.assign(root.style, {
      position: "fixed",
      inset: "0",
      pointerEvents: "none",
      zIndex: "100",
      overflow: "hidden",
    } as CSSStyleDeclaration);
    document.body.appendChild(root);
    const N = 80;
    for (let i = 0; i < N; i++) {
      const piece = document.createElement("span");
      const size = 6 + Math.random() * 6;
      Object.assign(piece.style, {
        position: "absolute",
        top: "-10px",
        left: `${Math.random() * 100}%`,
        width: `${size}px`,
        height: `${size}px`,
        background: colors[i % colors.length],
        borderRadius: "2px",
        transform: `rotate(${Math.random() * 360}deg)`,
        opacity: "0.9",
        animation: `vayobd-confetti ${1.4 + Math.random() * 0.8}s ease-out forwards`,
        animationDelay: `${Math.random() * 0.2}s`,
      } as CSSStyleDeclaration);
      root.appendChild(piece);
    }
    const style = document.createElement("style");
    style.textContent = `@keyframes vayobd-confetti { to { transform: translateY(110vh) rotate(720deg); opacity: 0; } }`;
    document.head.appendChild(style);
    const timeout = window.setTimeout(() => {
      root.remove();
      style.remove();
    }, 2500);
    return () => {
      window.clearTimeout(timeout);
      root.remove();
      style.remove();
    };
  }, [fire, done]);
}
