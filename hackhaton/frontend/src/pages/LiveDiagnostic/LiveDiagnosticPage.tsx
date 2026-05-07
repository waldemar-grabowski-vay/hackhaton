/**
 * LiveDiagnosticPage (T016 stub — full implementation in T028, Phase 3 / US1).
 *
 * Phase 2 deliverable: a stub that proves the route works and that
 * Developer-mode-off operators get redirected to the main page. The
 * actual host picker, state panel, errq panel, and raw-frames log are
 * implemented in US1 / US2 / US3.
 */
import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";

import { healthSchema, type Health } from "@/api/schemas";

async function fetchHealth(): Promise<Health> {
  const resp = await fetch("/api/health");
  if (!resp.ok) throw new Error(`health: ${resp.status}`);
  return healthSchema.parse(await resp.json());
}

export function LiveDiagnosticPage() {
  const { data, isLoading } = useQuery<Health>({
    queryKey: ["health-live"],
    queryFn: fetchHealth,
    staleTime: 30_000,
    retry: false,
  });
  if (isLoading) return null;
  if (!data?.live_diagnostic?.enabled) {
    return <Navigate to="/" replace />;
  }
  const live = data.live_diagnostic;
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Live diagnostic</h1>
        <p className="text-muted-foreground text-sm">
          Developer-mode surface for live CAN inspection. Pick a host and
          connect to start streaming. (Full UI ships in US1 / US2 / US3.)
        </p>
      </header>
      <section className="space-y-2 rounded-md border bg-card/50 p-4 text-sm">
        <h2 className="font-medium">Backend status</h2>
        <ul className="space-y-1 text-muted-foreground">
          <li>
            ERRQ model:{" "}
            <span className={live.errq_loaded ? "text-success" : "text-destructive"}>
              {live.errq_loaded ? "loaded" : "degraded"}
            </span>
            {live.errq_source_path ? <span> — {live.errq_source_path}</span> : null}
            {live.errq_load_error ? (
              <span className="block text-xs text-destructive">{live.errq_load_error}</span>
            ) : null}
          </li>
          <li>
            DBC:{" "}
            <span className={live.dbc_loaded ? "text-success" : "text-destructive"}>
              {live.dbc_loaded ? "loaded" : "degraded"}
            </span>
            {live.dbc_source_path ? <span> — {live.dbc_source_path}</span> : null}
            {live.dbc_load_error ? (
              <span className="block text-xs text-destructive">{live.dbc_load_error}</span>
            ) : null}
          </li>
        </ul>
      </section>
    </div>
  );
}
