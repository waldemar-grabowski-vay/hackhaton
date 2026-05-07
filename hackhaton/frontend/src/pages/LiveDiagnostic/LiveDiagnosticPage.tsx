/**
 * LiveDiagnosticPage (T028).
 *
 * Surface state machine:
 *   - idle:        HostPicker is shown.
 *   - connecting:  Loading state with the picked host id + "Cancel" button.
 *   - connected:   StatePanel + status header (with Disconnect).
 *   - lost:        "Connection lost" banner with stderr + Reconnect.
 *
 * Errq + filters/channel toggle / raw frames / pause-resume-clear are
 * Phases 4 + 5 (US2 + US3).
 */
import { useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, CircleSlash, Loader2, RotateCcw, X } from "lucide-react";
import { Link, Navigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { healthSchema, type Health } from "@/api/schemas";
import { HostPicker } from "@/pages/LiveDiagnostic/HostPicker";
import { StatePanel } from "@/pages/LiveDiagnostic/StatePanel";
import { useLiveSession, type LiveSessionConnectArgs } from "@/pages/LiveDiagnostic/useLiveSession";

async function fetchHealth(): Promise<Health> {
  const resp = await fetch("/api/health");
  if (!resp.ok) throw new Error(`health: ${resp.status}`);
  return healthSchema.parse(await resp.json());
}

export function LiveDiagnosticPage() {
  const health = useQuery<Health>({
    queryKey: ["health-live"],
    queryFn: fetchHealth,
    staleTime: 30_000,
    retry: false,
  });
  const session = useLiveSession();
  const [lastConnect, setLastConnect] = useState<LiveSessionConnectArgs | null>(null);

  const onConnect = useCallback(
    (args: LiveSessionConnectArgs) => {
      setLastConnect(args);
      session.connect(args);
    },
    [session],
  );

  const onFilterChange = useCallback(
    (substring: string) => {
      session.send({
        kind: "set_filter",
        payload: { signal_name_substring: substring },
      });
    },
    [session],
  );

  if (health.isLoading) return null;
  if (!health.data?.live_diagnostic?.enabled) {
    return <Navigate to="/" replace />;
  }
  const live = health.data.live_diagnostic;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Button asChild variant="ghost" size="sm" className="-ml-2 mb-1 gap-1">
            <Link to="/">
              <ArrowLeft className="h-3 w-3" /> Back to picker
            </Link>
          </Button>
          <h1 className="text-2xl font-semibold">Live diagnostic</h1>
          <p className="text-muted-foreground text-sm">
            Stream live CAN traffic from a TS testbed via your local{" "}
            <code>ssh</code>. Read-only.
          </p>
        </div>
        <BackendStatus live={live} />
      </header>

      {session.state.status === "idle" ? (
        <section className="rounded-md border bg-card/40 p-4">
          <HostPicker onConnect={onConnect} />
        </section>
      ) : null}

      {session.state.status === "connecting" ? (
        <ConnectingBanner hostId={lastConnect?.hostId ?? ""} onCancel={session.disconnect} />
      ) : null}

      {session.state.status === "connected" ? (
        <ConnectedView
          hostId={lastConnect?.hostId ?? ""}
          signals={session.state.signals}
          ready={session.state.ready}
          onDisconnect={session.disconnect}
          onFilterChange={onFilterChange}
        />
      ) : null}

      {session.state.status === "lost" ? (
        <LostBanner
          reason={session.state.reason}
          stderr={session.state.stderr}
          onReconnect={() => lastConnect && onConnect(lastConnect)}
          onIdle={session.disconnect}
        />
      ) : null}
    </div>
  );
}

function BackendStatus({ live }: { live: NonNullable<Health["live_diagnostic"]> }) {
  return (
    <div className="text-xs space-y-1 rounded-md border bg-card/40 px-3 py-2 text-muted-foreground">
      <div>
        ERRQ:{" "}
        <span className={live.errq_loaded ? "text-success" : "text-destructive"}>
          {live.errq_loaded ? "loaded" : "degraded"}
        </span>
      </div>
      <div>
        DBC:{" "}
        <span className={live.dbc_loaded ? "text-success" : "text-destructive"}>
          {live.dbc_loaded ? "loaded" : "degraded"}
        </span>
        {live.dbc_source_path ? (
          <span className="ml-1 truncate">— {trimPath(live.dbc_source_path)}</span>
        ) : null}
      </div>
    </div>
  );
}

function ConnectingBanner({ hostId, onCancel }: { hostId: string; onCancel: () => void }) {
  return (
    <section className="flex items-center gap-3 rounded-md border bg-card/40 p-4">
      <Loader2 className="h-4 w-4 animate-spin" />
      <span className="text-sm">
        Connecting to <code>{hostId}</code>…
      </span>
      <Button onClick={onCancel} variant="ghost" size="sm" className="ml-auto">
        <X className="mr-1 h-3 w-3" /> Cancel
      </Button>
    </section>
  );
}

function ConnectedView({
  hostId,
  signals,
  ready,
  onDisconnect,
  onFilterChange,
}: {
  hostId: string;
  signals: ReturnType<typeof useLiveSession>["state"]["signals"];
  ready: ReturnType<typeof useLiveSession>["state"]["ready"];
  onDisconnect: () => void;
  onFilterChange: (s: string) => void;
}) {
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center gap-3 rounded-md border bg-success/10 p-3 text-sm">
        <span className="rounded-full bg-success/20 px-2 py-0.5 text-xs text-success">
          Connected
        </span>
        <span className="font-mono">{hostId}</span>
        <span className="text-muted-foreground text-xs">
          session {ready.sessionId?.slice(0, 8)}…
        </span>
        <Button onClick={onDisconnect} variant="outline" size="sm" className="ml-auto">
          Disconnect
        </Button>
      </div>
      <StatePanel signals={signals} onFilterChange={onFilterChange} />
    </section>
  );
}

function LostBanner({
  reason,
  stderr,
  onReconnect,
  onIdle,
}: {
  reason: string | null;
  stderr: string | null;
  onReconnect: () => void;
  onIdle: () => void;
}) {
  return (
    <section className="space-y-3 rounded-md border border-destructive/40 bg-destructive/5 p-4">
      <div className="flex items-center gap-2 text-destructive">
        <CircleSlash className="h-4 w-4" />
        <span className="text-sm font-medium">Connection lost</span>
      </div>
      {reason ? (
        <p className="text-sm">
          Reason: <code>{reason}</code>
        </p>
      ) : null}
      {stderr ? (
        <p className="text-muted-foreground text-xs">
          ssh said: <code className="break-all">{stderr}</code>
        </p>
      ) : null}
      <div className="flex gap-2">
        <Button onClick={onReconnect} size="sm" className="gap-1">
          <RotateCcw className="h-3 w-3" /> Reconnect
        </Button>
        <Button onClick={onIdle} size="sm" variant="ghost">
          Pick a different host
        </Button>
      </div>
    </section>
  );
}

function trimPath(p: string): string {
  if (p.length <= 40) return p;
  return "…" + p.slice(-40);
}
