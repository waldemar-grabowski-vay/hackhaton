/**
 * StatePanel (T027).
 *
 * Decoded signal table. Sorted by name. Renders up to 500 rows; sorts
 * by (channel, name) so A and B blocks group naturally. Filter input
 * is wired here — debounced 150 ms — and dispatches `set_filter` via
 * the parent's `send` callback.
 */
import { useEffect, useMemo, useRef, useState } from "react";

import type { DecodedSignal } from "@/api/liveSession";

interface StatePanelProps {
  signals: Map<string, DecodedSignal>;
  onFilterChange: (substring: string) => void;
}

const ROW_LIMIT = 500;

export function StatePanel({ signals, onFilterChange }: StatePanelProps) {
  const [filter, setFilter] = useState("");
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Local debounce — 150 ms — before pushing the filter upstream.
  useEffect(() => {
    if (debounce.current) clearTimeout(debounce.current);
    debounce.current = setTimeout(() => onFilterChange(filter), 150);
    return () => {
      if (debounce.current) clearTimeout(debounce.current);
    };
  }, [filter, onFilterChange]);

  // Client-side filter: applied to the *currently visible* signal list
  // independently of the upstream `set_filter` envelope. The upstream
  // filter reduces what the backend sends; the client-side filter
  // hides rows already in our local Map (otherwise the user types
  // "BRAKE" and still sees stale non-brake rows from before).
  const rows = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    const list = Array.from(signals.values()).filter((s) =>
      needle ? s.name.toLowerCase().includes(needle) : true,
    );
    list.sort((a, b) => {
      if (a.channel !== b.channel) {
        if (a.channel === "A") return -1;
        if (b.channel === "A") return 1;
        if (a.channel === "B") return -1;
        if (b.channel === "B") return 1;
      }
      return a.name.localeCompare(b.name);
    });
    return list.slice(0, ROW_LIMIT);
  }, [signals, filter]);

  const total = signals.size;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <input
          type="search"
          placeholder="Filter signals (e.g. BRAKE)"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="flex-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm"
        />
        <span className="text-muted-foreground whitespace-nowrap text-xs">
          {rows.length}/{total}
        </span>
      </div>
      <div className="rounded-md border bg-card/30">
        {rows.length === 0 ? (
          <p className="text-muted-foreground p-4 text-sm">
            No signals decoded yet. Check the DBC path if this persists.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b text-muted-foreground text-xs uppercase tracking-wide">
              <tr>
                <th className="px-3 py-2 text-left">Signal</th>
                <th className="px-3 py-2 text-left">Value</th>
                <th className="px-3 py-2 text-left">Ch</th>
                <th className="px-3 py-2 text-right">CAN id</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((sig, i) => (
                <tr
                  key={`${sig.name}::${sig.channel}`}
                  className={i % 2 ? "bg-muted/30" : ""}
                >
                  <td className="px-3 py-1.5 font-mono text-xs">{sig.name}</td>
                  <td className="px-3 py-1.5 font-mono text-xs">
                    {formatValue(sig.value)}
                  </td>
                  <td className="px-3 py-1.5 text-xs">{sig.channel}</td>
                  <td className="px-3 py-1.5 text-right font-mono text-xs">
                    0x{sig.can_id.toString(16).toUpperCase()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function formatValue(v: DecodedSignal["value"]): string {
  if (v === null) return "—";
  if (typeof v === "number") {
    return Number.isInteger(v) ? v.toString() : v.toFixed(3);
  }
  if (typeof v === "boolean") return v ? "true" : "false";
  return String(v);
}
