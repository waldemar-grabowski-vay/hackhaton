/**
 * useLiveSession (T025).
 *
 * Opens one WebSocket per session against `/api/live/{host_id}/ws`,
 * parses incoming envelopes via `parseServerEnvelope`, exposes the
 * accumulated decoded signals + active errq entries + raw frames, and
 * dispatches outbound control envelopes (set_filter, set_channel,
 * pause, resume, clear, toggle_raw_frames).
 *
 * Lifecycle the consumer sees:
 *   idle → connecting → connected → lost (with optional reason) → idle
 */
import { useCallback, useEffect, useRef, useState } from "react";

import {
  parseServerEnvelope,
  type ClientEnvelope,
  type DecodedSignal,
  type ErrqEntry,
  type RawFrame,
  type ServerEnvelope,
} from "@/api/liveSession";

const RAW_FRAME_RING_MAX = 500; // FR-014

export type LiveStatus = "idle" | "connecting" | "connected" | "lost";

export interface LiveSessionState {
  status: LiveStatus;
  reason: string | null;
  stderr: string | null;
  signals: Map<string, DecodedSignal>;
  errq: ErrqEntry[];
  rawFrames: RawFrame[];
  ready: {
    sessionId: string | null;
    errqLoaded: boolean;
    dbcLoaded: boolean;
  };
  pauseBufferCount: number;
}

export interface LiveSessionConnectArgs {
  hostId: string;
  user?: string;
  port?: number;
}

export interface LiveSession {
  state: LiveSessionState;
  connect: (args: LiveSessionConnectArgs) => void;
  disconnect: () => void;
  send: (env: ClientEnvelope) => void;
}

const initialState: LiveSessionState = {
  status: "idle",
  reason: null,
  stderr: null,
  signals: new Map(),
  errq: [],
  rawFrames: [],
  ready: { sessionId: null, errqLoaded: false, dbcLoaded: false },
  pauseBufferCount: 0,
};

export function useLiveSession(): LiveSession {
  const [state, setState] = useState<LiveSessionState>(initialState);
  const wsRef = useRef<WebSocket | null>(null);

  const handleEnvelope = useCallback((env: ServerEnvelope) => {
    setState((prev) => {
      switch (env.kind) {
        case "ready": {
          return {
            ...prev,
            ready: {
              sessionId: env.payload.session_id,
              errqLoaded: env.payload.errq_loaded,
              dbcLoaded: env.payload.dbc_loaded,
            },
          };
        }
        case "status": {
          return {
            ...prev,
            status:
              env.payload.state === "closed" ? "idle" : (env.payload.state as LiveStatus),
            reason: env.payload.reason ?? null,
            stderr: env.payload.ssh_stderr_first_line ?? null,
            pauseBufferCount: env.payload.pause_buffer_count ?? 0,
          };
        }
        case "signal_update": {
          const next = new Map(prev.signals);
          for (const sig of env.payload.signals) {
            const key = `${sig.name}::${sig.channel}`;
            next.set(key, sig);
          }
          return { ...prev, signals: next };
        }
        case "errq_update": {
          let next = prev.errq.slice();
          if (env.payload.disappeared.length) {
            const dropped = new Set(
              env.payload.disappeared.map(
                (k) => `${k.channel}|${k.byte}|${k.bit}`,
              ),
            );
            next = next.filter(
              (e) => !dropped.has(`${e.channel}|${e.byte}|${e.bit}`),
            );
          }
          if (env.payload.appeared.length) {
            const incoming = new Map<string, ErrqEntry>();
            for (const e of next)
              incoming.set(`${e.channel}|${e.byte}|${e.bit}`, e);
            for (const e of env.payload.appeared)
              incoming.set(`${e.channel}|${e.byte}|${e.bit}`, e);
            next = Array.from(incoming.values());
          }
          return { ...prev, errq: next };
        }
        case "raw_frame": {
          const next = prev.rawFrames.concat(env.payload);
          if (next.length > RAW_FRAME_RING_MAX) {
            next.splice(0, next.length - RAW_FRAME_RING_MAX);
          }
          return { ...prev, rawFrames: next };
        }
        case "error": {
          return { ...prev, reason: env.payload.message };
        }
      }
    });
  }, []);

  const disconnect = useCallback(() => {
    const ws = wsRef.current;
    if (ws) {
      try {
        ws.close(1000, "client_disconnect");
      } catch {
        // ignore
      }
      wsRef.current = null;
    }
    setState(initialState);
  }, []);

  const connect = useCallback(
    ({ hostId, user, port }: LiveSessionConnectArgs) => {
      // Tear down any previous connection.
      const previous = wsRef.current;
      if (previous) {
        try {
          previous.close();
        } catch {
          // ignore
        }
        wsRef.current = null;
      }

      const params = new URLSearchParams({ developer_mode_check: "1" });
      if (user) params.set("user", user);
      if (port !== undefined) params.set("port", String(port));

      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      const url = `${proto}://${window.location.host}/api/live/${encodeURIComponent(
        hostId,
      )}/ws?${params.toString()}`;

      setState({ ...initialState, status: "connecting" });
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          const env = parseServerEnvelope(data);
          if (env) handleEnvelope(env);
        } catch {
          // ignore malformed messages
        }
      };
      ws.onerror = () => {
        setState((prev) => ({ ...prev, status: "lost", reason: "ws_error" }));
      };
      ws.onclose = (ev) => {
        setState((prev) => {
          // If the server already pushed a "lost" status, keep it; else
          // synthesise one from the close code.
          if (prev.status === "lost" || prev.status === "idle") return prev;
          return {
            ...prev,
            status: "lost",
            reason: prev.reason ?? closeCodeReason(ev.code),
          };
        });
        wsRef.current = null;
      };
    },
    [handleEnvelope],
  );

  const send = useCallback((env: ClientEnvelope) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    try {
      ws.send(JSON.stringify(env));
    } catch {
      // ignore
    }
  }, []);

  // Tear down on unmount.
  useEffect(() => () => disconnect(), [disconnect]);

  return { state, connect, disconnect, send };
}

function closeCodeReason(code: number): string {
  switch (code) {
    case 1008:
      return "policy_violation";
    case 1011:
      return "internal_error";
    case 4000:
      return "ssh_failed";
    case 4001:
      return "ssh_stalled";
    default:
      return `closed_${code}`;
  }
}
