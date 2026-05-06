/**
 * StatusDonut (T051).
 *
 * Tiny Recharts donut showing the working / needs-attention split. Sized for
 * the result hero card; not interactive — purely decorative reinforcement of
 * the headline number.
 */
import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";

interface StatusDonutProps {
  working: number;
  needsAttention: number;
  size?: number;
}

export function StatusDonut({ working, needsAttention, size = 132 }: StatusDonutProps) {
  const total = working + needsAttention;
  const allHealthy = total > 0 && needsAttention === 0;
  const data =
    total === 0
      ? [{ name: "empty", value: 1 }]
      : [
          { name: "Working", value: working },
          { name: "Needs attention", value: needsAttention },
        ];

  return (
    <div
      className="relative grid place-items-center"
      style={{ width: size, height: size }}
      aria-label={`${working} working, ${needsAttention} needs attention`}
    >
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            innerRadius={size * 0.36}
            outerRadius={size * 0.48}
            startAngle={90}
            endAngle={-270}
            stroke="none"
            isAnimationActive
            animationDuration={520}
          >
            {total === 0 ? (
              <Cell fill="hsl(var(--muted))" />
            ) : (
              <>
                <Cell fill="hsl(var(--success))" />
                <Cell fill="hsl(var(--warning))" />
              </>
            )}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 grid place-items-center">
        <div className="text-center leading-tight">
          <div className="text-2xl font-semibold tabular-nums text-foreground">
            {working}
            <span className="text-muted-foreground/70">/{total}</span>
          </div>
          <div
            className={
              allHealthy
                ? "text-[11px] font-medium uppercase tracking-wide text-success"
                : "text-[11px] font-medium uppercase tracking-wide text-warning"
            }
          >
            {allHealthy ? "All healthy" : "Items"}
          </div>
        </div>
      </div>
    </div>
  );
}
