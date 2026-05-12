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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { healthSchema, type Health } from "@/api/schemas";
import { ChannelToggle, type Channel } from "@/pages/LiveDiagnostic/ChannelToggle";
import { ErrqPanel } from "@/pages/LiveDiagnostic/ErrqPanel";
import { HostPicker } from "@/pages/LiveDiagnostic/HostPicker";
import { PlaybackControls } from "@/pages/LiveDiagnostic/PlaybackControls";
import { RawFramesLog } from "@/pages/LiveDiagnostic/RawFramesLog";
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

  const [channel, setChannel] = useState<Channel>("both");
  const [paused, setPaused] = useState(false);
  const [rawEnabled, setRawEnabled] = useState(false);

  const onFilterChange = useCallback(
    (substring: string) => {
      session.send({
        kind: "set_filter",
        payload: { signal_name_substring: substring },
      });
    },
    [session],
  );

  const onChannelChange = useCallback(
    (next: Channel) => {
      setChannel(next);
      session.send({ kind: "set_channel", payload: { channel: next } });
    },
    [session],
  );

  const onPause = useCallback(() => {
    setPaused(true);
    session.send({ kind: "pause", payload: {} });
  }, [session]);

  const onResume = useCallback(() => {
    setPaused(false);
    session.send({ kind: "resume", payload: {} });
  }, [session]);

  const onClear = useCallback(() => {
    session.send({ kind: "clear", payload: {} });
  }, [session]);

  const onToggleRawFrames = useCallback(
    (enabled: boolean) => {
      setRawEnabled(enabled);
      session.send({ kind: "toggle_raw_frames", payload: { enabled } });
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
          errq={session.state.errq}
          rawFrames={session.state.rawFrames}
          ready={session.state.ready}
          channel={channel}
          paused={paused}
          rawEnabled={rawEnabled}
          pauseBufferCount={session.state.pauseBufferCount}
          onDisconnect={session.disconnect}
          onFilterChange={onFilterChange}
          onChannelChange={onChannelChange}
          onPause={onPause}
          onResume={onResume}
          onClear={onClear}
          onToggleRawFrames={onToggleRawFrames}
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
  errq,
  rawFrames,
  ready,
  channel,
  paused,
  rawEnabled,
  pauseBufferCount,
  onDisconnect,
  onFilterChange,
  onChannelChange,
  onPause,
  onResume,
  onClear,
  onToggleRawFrames,
}: {
  hostId: string;
  signals: ReturnType<typeof useLiveSession>["state"]["signals"];
  errq: ReturnType<typeof useLiveSession>["state"]["errq"];
  rawFrames: ReturnType<typeof useLiveSession>["state"]["rawFrames"];
  ready: ReturnType<typeof useLiveSession>["state"]["ready"];
  channel: Channel;
  paused: boolean;
  rawEnabled: boolean;
  pauseBufferCount: number;
  onDisconnect: () => void;
  onFilterChange: (s: string) => void;
  onChannelChange: (c: Channel) => void;
  onPause: () => void;
  onResume: () => void;
  onClear: () => void;
  onToggleRawFrames: (enabled: boolean) => void;
}) {
  // Client-side channel filtering: server set_channel narrows the next
  // envelope, but accumulated state needs the same filter applied here
  // so the user sees the change instantly (US3 acceptance scenario 2).
  const visibleErrq = channel === "both" ? errq : errq.filter((e) => e.channel === channel);

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
        {visibleErrq.length > 0 ? (
          <span className="rounded-full bg-destructive/15 px-2 py-0.5 text-xs text-destructive">
            {visibleErrq.length} active error{visibleErrq.length === 1 ? "" : "s"}
          </span>
        ) : null}
        <Button onClick={onDisconnect} variant="outline" size="sm" className="ml-auto">
          Disconnect
        </Button>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <ChannelToggle value={channel} onChange={onChannelChange} />
        <PlaybackControls
          paused={paused}
          pauseBufferCount={pauseBufferCount}
          onPause={onPause}
          onResume={onResume}
          onClear={onClear}
        />
      </div>

      {/* Phone (<md): three-tab layout. Desktop (md+): side-by-side
          panels with the raw-frames log below. */}
      <div className="md:hidden">
        <Tabs defaultValue="signals">
          <TabsList className="w-full">
            <TabsTrigger value="signals" className="flex-1">
              Signals
            </TabsTrigger>
            <TabsTrigger value="errq" className="flex-1">
              REECU{visibleErrq.length > 0 ? ` (${visibleErrq.length})` : ""}
            </TabsTrigger>
            <TabsTrigger value="raw" className="flex-1">
              Raw
            </TabsTrigger>
          </TabsList>
          <TabsContent value="signals">
            <StatePanel
              signals={signals}
              channel={channel}
              onFilterChange={onFilterChange}
            />
          </TabsContent>
          <TabsContent value="errq">
            <ErrqPanel entries={visibleErrq} errqLoaded={ready.errqLoaded} />
          </TabsContent>
          <TabsContent value="raw">
            <RawFramesLog
              frames={rawFrames}
              enabled={rawEnabled}
              onToggle={onToggleRawFrames}
            />
          </TabsContent>
        </Tabs>
      </div>
      <div className="hidden md:block md:space-y-4">
        <div className="grid gap-4 md:grid-cols-[1fr_minmax(280px,360px)]">
          <div className="min-w-0">
            <StatePanel
              signals={signals}
              channel={channel}
              onFilterChange={onFilterChange}
            />
          </div>
          <aside className="space-y-2">
            <h2 className="text-sm font-semibold">REECU error queue</h2>
            <ErrqPanel entries={visibleErrq} errqLoaded={ready.errqLoaded} />
          </aside>
        </div>
        <RawFramesLog
          frames={rawFrames}
          enabled={rawEnabled}
          onToggle={onToggleRawFrames}
        />
      </div>
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
