/**
 * PlaybackControls (T042).
 *
 * Pause / Resume / Clear buttons. The Clear action is destructive (it
 * resets the local accumulator + tells the server to drop everything),
 * so per US3 acceptance scenario 4 we gate it behind a confirm dialog.
 *
 * The pause state is derived from the parent — when paused, the
 * backend keeps decoding but suppresses signal_update envelopes; the
 * `pause_buffer_count` from `status` envelopes shows how many decoded
 * signals are queued.
 */
import { useState } from "react";
import { Pause, Play, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface PlaybackControlsProps {
  paused: boolean;
  pauseBufferCount: number;
  onPause: () => void;
  onResume: () => void;
  onClear: () => void;
}

export function PlaybackControls({
  paused,
  pauseBufferCount,
  onPause,
  onResume,
  onClear,
}: PlaybackControlsProps) {
  const [confirming, setConfirming] = useState(false);

  return (
    <div className="flex flex-wrap items-center gap-2">
      {paused ? (
        <Button onClick={onResume} size="sm" variant="default" className="gap-1">
          <Play className="h-3 w-3" />
          Resume
        </Button>
      ) : (
        <Button onClick={onPause} size="sm" variant="outline" className="gap-1">
          <Pause className="h-3 w-3" />
          Pause
        </Button>
      )}
      <Button
        onClick={() => setConfirming(true)}
        size="sm"
        variant="ghost"
        className="gap-1"
      >
        <Trash2 className="h-3 w-3" />
        Clear
      </Button>
      {paused ? (
        <span className="text-muted-foreground text-xs">
          Paused · {pauseBufferCount} frame{pauseBufferCount === 1 ? "" : "s"}{" "}
          buffered
        </span>
      ) : null}

      <Dialog open={confirming} onOpenChange={setConfirming}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Clear live state?</DialogTitle>
            <DialogDescription>
              This wipes every decoded signal, the active REECU error queue,
              and the raw-frames log on this page. The testbed itself is not
              affected — frames will continue arriving.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="ghost" size="sm" onClick={() => setConfirming(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => {
                onClear();
                setConfirming(false);
              }}
            >
              Clear everything
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
