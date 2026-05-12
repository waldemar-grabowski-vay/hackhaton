/**
 * AppFooter — tiny version-info row at the bottom of the SPA (spec 006 / FR-013 / US4).
 *
 * Reads `version` + `engine_version` from `/api/health` (already exposed). Renders a
 * single muted line so a user / support engineer can answer "what version do I have"
 * without opening a terminal.
 */
import { useQuery } from "@tanstack/react-query";

interface HealthBlock {
  status: string;
  version: string;
  engine_version: string | null;
}

async function fetchHealth(): Promise<HealthBlock> {
  const resp = await fetch("/api/health");
  if (!resp.ok) throw new Error(`health: ${resp.status}`);
  return (await resp.json()) as HealthBlock;
}

export function AppFooter() {
  const { data } = useQuery({
    queryKey: ["health", "footer"],
    queryFn: fetchHealth,
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
  });

  if (!data) return null;
  const engine = data.engine_version ? `engine ${data.engine_version}` : "engine —";
  return (
    <footer className="mt-12 border-t border-border/40 px-4 py-3 text-center text-xs text-muted-foreground">
      VayOBD {data.version} · {engine}
    </footer>
  );
}
