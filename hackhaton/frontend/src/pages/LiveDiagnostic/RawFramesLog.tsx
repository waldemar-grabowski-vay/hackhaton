/**
 * RawFramesLog (T043).
 *
 * Capped 500-line monospace log. The hook already enforces the ring
 * buffer (RAW_FRAME_RING_MAX = 500) so this component just renders the
 * tail with a toggle button that flips `LiveFilter.raw_frames_enabled`
 * server-side.
 *
 * No virtualization library — at 500 rows × ~40px the DOM stays under
 * 20k px and modern browsers paint that comfortably. We auto-scroll to
 * the bottom when new frames arrive unless the user has scrolled up
 * (so manual inspection isn't yanked away mid-read).
 */
import { useEffect, useRef } from "react";
import { Activity, ToggleLeft, ToggleRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { RawFrame } from "@/api/liveSession";

interface RawFramesLogProps {
  frames: RawFrame[];
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
}

export function RawFramesLog({ frames, enabled, onToggle }: RawFramesLogProps) {
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const stickToBottomRef = useRef(true);

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el || !stickToBottomRef.current) return;
    el.scrollTop = el.scrollHeight;
  }, [frames]);

  function handleScroll() {
    const el = scrollerRef.current;
    if (!el) return;
    const slack = 40;
    stickToBottomRef.current =
      el.scrollHeight - el.scrollTop - el.clientHeight < slack;
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm">
          <Activity className="h-3 w-3" />
          <span className="font-medium">Raw frames</span>
          <span className="text-muted-foreground text-xs">
            {frames.length}/500
          </span>
        </div>
        <Button
          onClick={() => onToggle(!enabled)}
          size="sm"
          variant="outline"
          className="gap-1"
        >
          {enabled ? (
            <>
              <ToggleRight className="h-3 w-3" /> On
            </>
          ) : (
            <>
              <ToggleLeft className="h-3 w-3" /> Off
            </>
          )}
        </Button>
      </div>
      {enabled ? (
        <div
          ref={scrollerRef}
          onScroll={handleScroll}
          className="h-64 overflow-auto rounded-md border bg-card/30 font-mono text-xs"
        >
          {frames.length === 0 ? (
            <p className="text-muted-foreground p-3 text-xs">
              Waiting for the first frame…
            </p>
          ) : (
            <ul className="p-2">
              {frames.map((f, i) => (
                <li key={`${f.at_ms}-${i}`} className="whitespace-nowrap">
                  <span className="text-muted-foreground">
                    {formatRelative(f.at_ms)}
                  </span>{" "}
                  <span>0x{f.can_id.toString(16).toUpperCase().padStart(3, "0")}</span>{" "}
                  <span className="text-muted-foreground">[{f.dlc}]</span>{" "}
                  <span>{f.payload_hex}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <p className="text-muted-foreground rounded-md border border-dashed p-3 text-xs">
          Raw-frame logging is off. Toggle it on to see every CAN frame as it
          arrives — useful for cross-checking the DBC decoder, but expect a
          dense scroll at 1000 fps.
        </p>
      )}
    </div>
  );
}

function formatRelative(atMs: number): string {
  const delta = Date.now() - atMs;
  if (delta < 1000) return `${delta}ms ago`;
  if (delta < 60_000) return `${(delta / 1000).toFixed(1)}s ago`;
  return `${Math.floor(delta / 60_000)}m ago`;
}
