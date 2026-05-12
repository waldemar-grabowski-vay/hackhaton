/**
 * HostDetailPage — version surface for one host.
 *
 * Shows the picked host's display name at the top, a response-level source
 * pill (live / unavailable), and three version cells (vDrive manifest,
 * vREECU, SEC), each with a per-field verdict (match / drift / no-manifest
 * / unavailable), a value, and an "as of" timestamp. An icon-button in the
 * top-right re-fetches with `?fresh=true` to bypass the 60 s server-side
 * TTL cache.
 *
 * Visual contract: `specs/007-ts-diag-restore-version-pull/contracts/frontend-states.md`.
 */
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  CircleSlash,
  Loader2,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useHostVersions, type VersionField, type VersionVerdict } from "@/api/hostVersions";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DiagnosticItemRow } from "@/components/result/DiagnosticItemRow";
import { ResultGroup } from "@/components/result/ResultGroup";
import { ResultHero } from "@/components/result/ResultHero";
import { PartialRunState } from "@/components/states/PartialRunState";
import { RunningState } from "@/components/states/RunningState";
import { UnreachableState } from "@/components/states/UnreachableState";
import { StaggeredItem, StaggeredList } from "@/components/motion/StaggeredList";
import { prettyHostName, strings } from "@/strings";
import type { DiagnosticRun, Host } from "@/api/schemas";

const FIELD_LABEL: Record<string, string> = {
  vdrive_manifest: strings.hostVersions.field.vdriveManifest,
  vreecu_version: strings.hostVersions.field.vreecuVersion,
  sec_version: strings.hostVersions.field.secVersion,
};

function formatTimeOfDay(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return iso;
  }
}

function verdictPill(verdict: VersionVerdict) {
  // Colour + icon — both required so the state is identifiable without
  // reading the small text (FR-010, SC-005).
  const map: Record<VersionVerdict, { label: string; tone: string; Icon: typeof CheckCircle2 }> = {
    match: {
      label: strings.hostVersions.verdict.match,
      tone: "border-emerald-500/40 bg-emerald-500/15 text-emerald-300",
      Icon: CheckCircle2,
    },
    drift: {
      label: strings.hostVersions.verdict.drift,
      tone: "border-amber-500/40 bg-amber-500/15 text-amber-200",
      Icon: AlertTriangle,
    },
    "no-manifest": {
      label: strings.hostVersions.verdict.noManifest,
      tone: "border-border bg-muted/60 text-muted-foreground",
      Icon: CircleSlash,
    },
    unavailable: {
      label: strings.hostVersions.verdict.unavailable,
      tone: "border-rose-500/40 bg-rose-500/15 text-rose-300",
      Icon: XCircle,
    },
  };
  const { label, tone, Icon } = map[verdict];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs ${tone}`}
      data-verdict={verdict}
    >
      <Icon className="h-3 w-3" aria-hidden />
      {label}
    </span>
  );
}

function VersionCell({
  fieldKey,
  field,
  loading,
}: {
  fieldKey: keyof typeof FIELD_LABEL;
  field: VersionField | undefined;
  loading: boolean;
}) {
  const label = FIELD_LABEL[fieldKey];

  // Loading state — em-dash + spinner (FR-020, Clarification Q4).
  if (loading || !field) {
    return (
      <div
        className="flex items-start justify-between gap-4 border-b border-border/40 py-3 last:border-b-0"
        data-field={fieldKey}
        data-state="loading"
      >
        <span className="text-sm text-muted-foreground">{label}</span>
        <span className="inline-flex items-center gap-2 font-mono text-sm text-muted-foreground">
          —
          <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
        </span>
      </div>
    );
  }

  // Steady states.
  const isUnavailable = field.verdict === "unavailable";
  return (
    <div
      className="flex flex-col gap-1 border-b border-border/40 py-3 last:border-b-0 md:flex-row md:items-start md:justify-between md:gap-4"
      data-field={fieldKey}
      data-state={field.verdict}
    >
      <span className="text-sm text-muted-foreground md:pt-0.5">{label}</span>
      <div className="flex flex-col items-end gap-1 text-right">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm">{isUnavailable ? "—" : field.value}</span>
          {verdictPill(field.verdict)}
        </div>
        {field.verdict === "drift" && field.expected ? (
          <p className="text-xs text-muted-foreground">
            {strings.hostVersions.expectedPrefix} <span className="font-mono">{field.expected}</span>
          </p>
        ) : null}
        {field.verdict === "no-manifest" ? (
          <p className="text-xs text-muted-foreground">{strings.hostVersions.noManifestHint}</p>
        ) : null}
        {isUnavailable && field.reason ? (
          <p className="text-xs text-muted-foreground">{field.reason}</p>
        ) : null}
        <p className="text-[11px] uppercase tracking-wider text-muted-foreground/80">
          {strings.hostVersions.asOfPrefix} {formatTimeOfDay(field.as_of)}
        </p>
      </div>
    </div>
  );
}

function SourcePill({
  source,
  hostId,
  loading,
}: {
  source: "live" | "unavailable" | undefined;
  hostId: string;
  loading: boolean;
}) {
  if (loading || !source) {
    return (
      <span
        className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-card/60 px-3 py-1 text-xs text-muted-foreground"
        data-source="loading"
      >
        <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
        {strings.hostVersions.loadingHint.replace("{host}", hostId)}
      </span>
    );
  }
  if (source === "live") {
    return (
      <span
        className="inline-flex items-center gap-2 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-300"
        data-source="live"
      >
        <CheckCircle2 className="h-3 w-3" aria-hidden />
        {strings.hostVersions.sourceLive.replace("{host}", hostId)}
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-2 rounded-full border border-rose-500/40 bg-rose-500/10 px-3 py-1 text-xs text-rose-300"
      data-source="unavailable"
    >
      <XCircle className="h-3 w-3" aria-hidden />
      {strings.hostVersions.sourceUnavailable.replace("{host}", hostId)}
    </span>
  );
}

export function HostDetailPage() {
  const { hostId } = useParams<{ hostId: string }>();
  // `refreshKey` increments each time the refresh button is clicked. We pass
  // it through React Query's `{ fresh }` parameter so cached and fresh fetches
  // are independent inflights.
  const [refreshKey, setRefreshKey] = useState(0);
  const fresh = refreshKey > 0;
  const query = useHostVersions(hostId, { fresh });

  if (!hostId) {
    return (
      <div className="mx-auto max-w-xl">
        <Card className="glass">
          <CardContent className="p-6 text-sm text-muted-foreground">
            No host selected.{" "}
            <Link to="/" className="text-primary underline">
              Pick one
            </Link>
            .
          </CardContent>
        </Card>
      </div>
    );
  }

  // Hard errors (404, 503, network) — never the engine-couldn't-reach-host
  // path which lands in the 200 body with source=unavailable.
  if (query.isError) {
    return (
      <div className="mx-auto max-w-xl space-y-4">
        <Button asChild variant="ghost" size="sm">
          <Link to="/">
            <ArrowLeft className="mr-2 h-4 w-4" aria-hidden />
            Back to host list
          </Link>
        </Button>
        <Card className="glass border-amber-400/40">
          <CardContent className="flex items-start gap-3 p-6">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-400" aria-hidden />
            <div>
              <p className="font-medium">Couldn't load host details.</p>
              <p className="text-sm text-muted-foreground">
                {query.error?.messageKey ?? "Try again in a moment."}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const loading = query.isPending || query.isFetching;
  const data = query.data;
  const heading = data ? prettyHostName(data.host.display_name, data.host.type) : hostId;
  const source = data?.source;

  function handleRefresh() {
    setRefreshKey((k) => k + 1);
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <Button asChild variant="ghost" size="sm" className="self-start">
        <Link to="/">
          <ArrowLeft className="mr-2 h-4 w-4" aria-hidden />
          Back to host list
        </Link>
      </Button>

      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">{heading}</h1>
        <p className="text-xs uppercase tracking-wider text-muted-foreground">{hostId}</p>
      </header>

      <Card className="glass">
        <CardContent className="space-y-3 p-6">
          <div className="flex items-center justify-between gap-3">
            <SourcePill source={source} hostId={hostId} loading={loading} />
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRefresh}
              disabled={loading}
              aria-label={strings.hostVersions.refreshButton}
              className="gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} aria-hidden />
              <span className="text-xs">
                {loading ? strings.hostVersions.refreshing : strings.hostVersions.refreshButton}
              </span>
            </Button>
          </div>

          <div className="pt-1">
            <VersionCell
              fieldKey="vdrive_manifest"
              field={data?.versions.vdrive_manifest}
              loading={loading}
            />
            <VersionCell
              fieldKey="vreecu_version"
              field={data?.versions.vreecu_version}
              loading={loading}
            />
            <VersionCell
              fieldKey="sec_version"
              field={data?.versions.sec_version}
              loading={loading}
            />
          </div>
        </CardContent>
      </Card>

      <CheckBatterySection run={data?.run ?? null} host={data?.host} loading={loading} />
    </div>
  );
}

/**
 * CheckBatterySection — restored result-page layout from pre-007, now
 * composed below the version card on the host-detail page (008 / US3).
 *
 * Renders Working / Needs attention groups from `run.items`, with the
 * dedicated state components for unreachable / partial / timeout outcomes.
 * REECU-owned rows are already filtered out by the backend (FR-011), so
 * `run.items` here is non-REECU only.
 */
function CheckBatterySection({
  run,
  host,
  loading,
}: {
  run: DiagnosticRun | null;
  host: Host | undefined;
  loading: boolean;
}) {
  const hostLabel = host ? prettyHostName(host.display_name, host.type) : "this host";
  if (loading && !run) {
    return (
      <Card className="glass">
        <CardContent className="p-6">
          <RunningState hostLabel={hostLabel} />
        </CardContent>
      </Card>
    );
  }
  if (!run || !host) return null;

  if (run.outcome === "unreachable" || run.outcome === "timeout") {
    return (
      <Card className="glass">
        <CardContent className="p-6">
          <UnreachableState outcome={run.outcome} hostLabel={hostLabel} />
        </CardContent>
      </Card>
    );
  }

  const working = run.items.filter((i) => i.status === "working");
  const needsAttention = run.items.filter((i) => i.status !== "working");

  return (
    <div className="space-y-5">
      <ResultHero
        host={host}
        startedAt={run.started_at}
        completedAt={run.completed_at}
        workingCount={working.length}
        needsAttentionCount={needsAttention.length}
      />

      {run.outcome === "partial" && <PartialRunState />}

      {needsAttention.length > 0 && (
        <ResultGroup
          variant="needs-attention"
          title={strings.result.needsAttentionHeading}
          count={needsAttention.length}
        >
          <StaggeredList>
            {needsAttention.map((item) => (
              <StaggeredItem key={item.id}>
                <DiagnosticItemRow item={item} hostType={host.type} />
              </StaggeredItem>
            ))}
          </StaggeredList>
        </ResultGroup>
      )}

      {working.length > 0 && (
        <ResultGroup
          variant="working"
          title={strings.result.workingHeading}
          count={working.length}
          collapsible
          defaultExpanded={false}
        >
          <StaggeredList>
            {working.map((item) => (
              <StaggeredItem key={item.id}>
                <DiagnosticItemRow item={item} hostType={host.type} />
              </StaggeredItem>
            ))}
          </StaggeredList>
        </ResultGroup>
      )}
    </div>
  );
}
