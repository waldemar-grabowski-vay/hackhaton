/**
 * RunResultPage (T057 + T060 + T064 + T066).
 *
 * - On mount, kicks off `useRunCheck(hostId)` once.
 * - Shows `RunningState` while in flight.
 * - On success, renders `ResultHero` + Working / Needs attention groups, with
 *   a `DiagnosticItemRow` for every catalog item the run produced.
 * - "Run check again" button (US2 / T060) re-runs against the same host and
 *   replaces the result data on success.
 * - Unreachable / timeout outcomes render the dedicated state.
 * - Partial outcomes prepend the partial banner.
 * - 100% pass + opt-in confetti via VITE_FEATURE_CONFETTI=true (T069).
 */
import { ArrowLeft, RotateCw } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { useInventory } from "@/api/inventory";
import { useLatestRun, useRunCheck } from "@/api/runs";
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
  const [searchParams, setSearchParams] = useSearchParams();
  const wantsAutoRun = searchParams.get("run") === "1";

  const inventory = useInventory();
  const host = useMemo(
    () => inventory.data?.hosts.find((h) => h.id === hostId) ?? null,
    [inventory.data, hostId],
  );

  const runMutation = useRunCheck(hostId);
  const latest = useLatestRun(hostId);

  const autoRunStartedRef = useRef(false);

  useEffect(() => {
    if (!hostId) return;
    if (!wantsAutoRun) return;
    if (autoRunStartedRef.current) return;
    if (runMutation.isPending) return;
    autoRunStartedRef.current = true;
    runMutation.mutate(undefined, {
      onSettled: () => {
        // Drop the ?run=1 from the URL so a refresh doesn't re-fire the check.
        setSearchParams({}, { replace: true });
      },
    });
  }, [hostId, wantsAutoRun, runMutation, setSearchParams]);

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

  // Prefer the freshest data: an in-flight or completed mutation wins, then the
  // persisted "latest" cache.
  const run = runMutation.data ?? latest.data ?? null;

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
        {(run || latest.data) && !isRunning && (
          <Button
            onClick={() => runMutation.mutate()}
            disabled={isRunning}
            className="gap-2"
          >
            <RotateCw className={isRunning ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
            {strings.runs.runAgainButton}
          </Button>
        )}
      </div>

      {isRunning && <RunningState hostLabel={hostLabel} />}

      {!isRunning && !run && latest.isLoading && (
        <Card className="glass">
          <CardContent className="p-6 text-sm text-muted-foreground">
            Loading…
          </CardContent>
        </Card>
      )}

      {!isRunning && !run && !latest.isLoading && (
        <Card className="glass">
          <CardContent className="space-y-3 p-6">
            <div className="text-sm font-semibold">
              {strings.runs.noneYet.title}
            </div>
            <div className="text-sm text-muted-foreground">
              {strings.runs.noneYet.body}
            </div>
            <Button onClick={() => runMutation.mutate()} className="mt-1">
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
              <DiagnosticItemRow item={item} />
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
              <DiagnosticItemRow item={item} />
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

