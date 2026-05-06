/**
 * UnreachableState (T055).
 *
 * Single user-facing message rendered when `outcome === "unreachable"` or
 * `"timeout"` (FR-006).
 */
import { motion } from "framer-motion";
import { CloudOff, TimerOff } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { strings } from "@/strings";

interface UnreachableStateProps {
  outcome: "unreachable" | "timeout";
  hostLabel: string;
}

export function UnreachableState({ outcome, hostLabel }: UnreachableStateProps) {
  const Icon = outcome === "timeout" ? TimerOff : CloudOff;
  const copy =
    outcome === "timeout" ? strings.outcomes.timeout : strings.outcomes.unreachable;
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      <Card className="glass-strong">
        <CardContent className="flex flex-col items-center gap-4 p-10 text-center">
          <div className="grid h-14 w-14 place-items-center rounded-full bg-destructive/10 text-destructive ring-1 ring-destructive/30">
            <Icon className="h-6 w-6" />
          </div>
          <div className="space-y-1">
            <div className="text-lg font-semibold">{copy.title}</div>
            <div className="text-sm text-muted-foreground">
              {copy.body} <span className="font-mono">{hostLabel}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
