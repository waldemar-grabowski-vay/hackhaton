/**
 * EmptyInventoryState.
 *
 * 002 / FR-013a: the refresh CTA from 001 is gone. This state now
 * surfaces only when the configured inventory file is missing or
 * unparseable; the recovery path is the "Inventory location"
 * affordance (US3, Phase 5) that re-opens the setup card.
 */
import { motion } from "framer-motion";
import { CloudOff } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { strings } from "@/strings";

export function EmptyInventoryState() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="mx-auto max-w-xl"
    >
      <Card className="glass-strong">
        <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
          <div className="grid h-14 w-14 place-items-center rounded-full bg-warning/10 text-warning ring-1 ring-warning/30">
            <CloudOff className="h-6 w-6" />
          </div>
          <div className="space-y-1">
            <div className="text-lg font-semibold">
              {strings.inventory.empty.title}
            </div>
            <div className="text-sm text-muted-foreground">
              {strings.inventory.empty.body}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
