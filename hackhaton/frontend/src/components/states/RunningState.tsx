/**
 * RunningState (T050).
 *
 * Renders while POST /api/runs is in flight. FR-009: a generic "running checks
 * against <host>" message; no per-item progress.
 */
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { strings } from "@/strings";

interface RunningStateProps {
  hostLabel: string;
}

export function RunningState({ hostLabel }: RunningStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.32 }}
    >
      <Card className="glass-strong">
        <CardContent className="flex flex-col items-center gap-5 p-10 text-center">
          <div className="relative grid h-16 w-16 place-items-center">
            <motion.span
              className="absolute inset-0 rounded-full bg-primary/10"
              animate={{ scale: [1, 1.18, 1], opacity: [0.4, 0.7, 0.4] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
            />
            <div className="relative grid h-12 w-12 place-items-center rounded-full bg-primary/20 text-primary ring-1 ring-primary/40">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-lg font-semibold">
              {strings.runs.inProgress}{" "}
              <span className="gradient-text">{hostLabel}</span>…
            </div>
            <div className="text-sm text-muted-foreground">
              {strings.runs.inProgressDetail}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
