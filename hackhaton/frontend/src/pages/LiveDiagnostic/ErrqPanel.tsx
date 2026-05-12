/**
 * ErrqPanel (T034).
 *
 * Active REECU error queue. Each row is one (channel, byte, bit) the
 * state tracker has classified as `active` server-side; the live diff
 * comes through `errq_update` envelopes and is folded into the hook's
 * `errq` array.
 *
 * - Severity badge maps the shared sun-theme palette (info/warn/error/
 *   critical → secondary/warning/destructive/destructive-strong).
 * - Channel pill mirrors the StatePanel "Ch" column for visual parity.
 * - Empty state is "No active errors".
 * - Degraded mode (errq_loaded === false in the `ready` envelope) flips
 *   to the FR-012 message — the REECU model failed to load on the
 *   backend and we cannot decode bits into names.
 */
import { CircleAlert, ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { ErrqEntry } from "@/api/liveSession";

interface ErrqPanelProps {
  entries: ErrqEntry[];
  errqLoaded: boolean;
}

type Severity = ErrqEntry["severity"];

export function ErrqPanel({ entries, errqLoaded }: ErrqPanelProps) {
  if (!errqLoaded) {
    return (
      <div className="rounded-md border border-warning/40 bg-warning/5 p-4">
        <div className="flex items-center gap-2 text-warning-foreground">
          <ShieldQuestion className="h-4 w-4" />
          <span className="text-sm font-medium">REECU error decoding unavailable</span>
        </div>
        <p className="text-muted-foreground mt-1 text-xs">
          The REECU error model failed to load on the backend. Raw byte
          values are still streamed through the Signals tab; symbolic
          names will return after the operator points{" "}
          <code>VAYOBD_REE_REECU_PATH</code> at a clone of{" "}
          <code>ree-reecu</code>.
        </p>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="rounded-md border bg-card/30 p-6 text-center">
        <ShieldCheck className="mx-auto mb-2 h-6 w-6 text-success" />
        <p className="text-sm font-medium">No active errors</p>
        <p className="text-muted-foreground text-xs">
          The REECU error queue is empty for this testbed right now.
        </p>
      </div>
    );
  }

  const sorted = [...entries].sort(sortBySeverityThenLocation);

  return (
    <ul className="space-y-2">
      {sorted.map((e) => (
        <li
          key={`${e.channel}|${e.byte}|${e.bit}`}
          className="rounded-md border bg-card/30 p-3"
        >
          {/* Top line: severity + channel + byte/bit (small, secondary).
              Wraps cleanly on narrow viewports. */}
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
            <SeverityBadge severity={e.severity} />
            <span className="rounded border border-border/60 bg-card/40 px-1.5 py-0.5 font-mono">
              Ch&nbsp;{e.channel}
            </span>
            <span className="font-mono">
              byte&nbsp;{e.byte}.{e.bit}
            </span>
          </div>
          {/* Error symbol — full width, monospace, allowed to wrap on
              underscores so 30+ char symbols don't blow out the layout. */}
          <p
            className="mt-1.5 break-all font-mono text-sm leading-snug"
            title={e.description}
          >
            {e.name ?? `bit ${e.byte}.${e.bit}`}
          </p>
          {e.description && e.description !== e.name ? (
            <p className="mt-1 text-xs text-muted-foreground">{e.description}</p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function SeverityBadge({ severity }: { severity: Severity }) {
  switch (severity) {
    case "critical":
      return (
        <Badge variant="destructive" className="gap-1 uppercase">
          <CircleAlert className="h-3 w-3" />
          Critical
        </Badge>
      );
    case "error":
      return (
        <Badge variant="destructive" className="gap-1 uppercase">
          <ShieldAlert className="h-3 w-3" />
          Error
        </Badge>
      );
    case "warn":
      return (
        <Badge variant="warning" className="uppercase">
          Warn
        </Badge>
      );
    case "info":
      return (
        <Badge variant="secondary" className="uppercase">
          Info
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="uppercase">
          —
        </Badge>
      );
  }
}

const SEVERITY_ORDER: Record<NonNullable<Severity>, number> = {
  critical: 0,
  error: 1,
  warn: 2,
  info: 3,
};

function sortBySeverityThenLocation(a: ErrqEntry, b: ErrqEntry): number {
  const aRank = a.severity ? SEVERITY_ORDER[a.severity] : 4;
  const bRank = b.severity ? SEVERITY_ORDER[b.severity] : 4;
  if (aRank !== bRank) return aRank - bRank;
  if (a.channel !== b.channel) return a.channel.localeCompare(b.channel);
  if (a.byte !== b.byte) return a.byte - b.byte;
  return a.bit - b.bit;
}
