/**
 * PartialRunState (T056).
 *
 * Banner shown above the result groups when `outcome === "partial"` to make
 * the missing-some-checks situation explicit (FR-006).
 */
import { motion } from "framer-motion";
import { AlertTriangle } from "lucide-react";

import { strings } from "@/strings";

export function PartialRunState() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.32 }}
      className="flex items-start gap-3 rounded-xl border border-warning/30 bg-warning/5 p-4"
      role="status"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
      <div className="leading-tight">
        <div className="text-sm font-semibold text-warning-foreground/90">
          {strings.outcomes.partial.headline}
        </div>
        <div className="mt-0.5 text-xs text-muted-foreground">
          {strings.outcomes.partial.body}
        </div>
      </div>
    </motion.div>
  );
}
