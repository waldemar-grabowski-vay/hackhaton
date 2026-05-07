/**
 * HostPicker (T026).
 *
 * Host-only connection dialog. Per Q2 of clarify, the SPA never
 * collects SSH credentials — those live in the operator's `~/.ssh/`
 * and the backend invokes the local `ssh` binary. This component:
 *
 *   - Lists in-scope hosts from /api/inventory
 *   - Pre-selects the operator's last-used host (FR-016, F1) from
 *     browser localStorage
 *   - Optionally exposes user@/port overrides under "Show advanced"
 *   - Calls onConnect({hostId, user, port}) when the operator
 *     submits.
 *
 * No SSH credentials are stored — there are none to store.
 */
import { useEffect, useState } from "react";
import { Activity, ChevronDown, Plug } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useInventory } from "@/api/inventory";
import type { Host } from "@/api/schemas";

const STORAGE_KEY = "vayobd.live.hostSelection";

interface PersistedSelection {
  hostId: string;
  user?: string;
  port?: number;
}

interface HostPickerProps {
  onConnect: (args: { hostId: string; user?: string; port?: number }) => void;
}

function loadPersisted(): PersistedSelection | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedSelection;
    if (typeof parsed?.hostId === "string") return parsed;
  } catch {
    // ignore corrupted localStorage
  }
  return null;
}

function persist(selection: PersistedSelection): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(selection));
  } catch {
    // private mode / quota — best-effort, ignore
  }
}

export function HostPicker({ onConnect }: HostPickerProps) {
  const inventory = useInventory();
  const [hostId, setHostId] = useState<string | null>(null);
  const [user, setUser] = useState("");
  const [port, setPort] = useState("");
  const [advanced, setAdvanced] = useState(false);

  // Restore last selection on mount.
  useEffect(() => {
    const persisted = loadPersisted();
    if (persisted) {
      setHostId(persisted.hostId);
      setUser(persisted.user ?? "");
      setPort(persisted.port ? String(persisted.port) : "");
    }
  }, []);

  // Keep `hostId` valid against the loaded inventory.
  useEffect(() => {
    if (!inventory.data) return;
    const ids = new Set(inventory.data.hosts.map((h) => h.id));
    if (hostId && !ids.has(hostId)) setHostId(null);
  }, [inventory.data, hostId]);

  if (inventory.isLoading) {
    return <p className="text-muted-foreground text-sm">Loading hosts…</p>;
  }
  if (inventory.error || !inventory.data) {
    return (
      <p className="text-destructive text-sm">
        Couldn’t load the host list. Check that the backend is running and
        that <code>VAYOBD_INVENTORY_PATH</code> points at a valid clone.
      </p>
    );
  }

  // 004 is Developer-mode-only and only TS hosts are useful (the desktop
  // tool was TS-only). Ve hosts come through too but live diagnostic
  // against vehicles will surface no errq signals — keep them visible
  // but the ts hosts on top.
  const hosts = [...inventory.data.hosts].sort((a, b) => {
    if (a.type === b.type) return a.id.localeCompare(b.id);
    return a.type === "telestation" ? -1 : 1;
  });

  function submit() {
    if (!hostId) return;
    const userValue = user.trim() || undefined;
    const portNum = port.trim() ? Number.parseInt(port, 10) : undefined;
    if (port.trim() && (Number.isNaN(portNum) || portNum! < 1 || portNum! > 65535)) {
      return;
    }
    persist({ hostId, user: userValue, port: portNum });
    onConnect({ hostId, user: userValue, port: portNum });
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium">Host</label>
        <select
          value={hostId ?? ""}
          onChange={(e) => setHostId(e.target.value || null)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="">— pick a host —</option>
          {hosts.map((h: Host) => (
            <option key={h.id} value={h.id}>
              {h.id} ({h.type})
            </option>
          ))}
        </select>
      </div>
      <div>
        <button
          type="button"
          onClick={() => setAdvanced((v) => !v)}
          className="text-muted-foreground inline-flex items-center gap-1 text-xs hover:text-foreground"
        >
          <ChevronDown
            className={`h-3 w-3 transition ${advanced ? "rotate-0" : "-rotate-90"}`}
          />
          Show advanced (user@/port override)
        </button>
        {advanced ? (
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium">
                user@ override
              </label>
              <input
                type="text"
                value={user}
                onChange={(e) => setUser(e.target.value)}
                placeholder="(default from ~/.ssh/config)"
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium">port</label>
              <input
                type="number"
                value={port}
                onChange={(e) => setPort(e.target.value)}
                placeholder="22"
                min={1}
                max={65535}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              />
            </div>
          </div>
        ) : null}
      </div>
      <Button onClick={submit} disabled={!hostId} className="gap-2">
        <Plug className="h-4 w-4" />
        Connect
      </Button>
      <p className="text-muted-foreground text-xs">
        <Activity className="mr-1 inline h-3 w-3" />
        SSH credentials come from your local <code>~/.ssh/</code> — the SPA
        never collects or stores them.
      </p>
    </div>
  );
}
