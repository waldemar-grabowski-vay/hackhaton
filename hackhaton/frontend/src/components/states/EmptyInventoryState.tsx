/**
 * EmptyInventoryState (T048).
 *
 * Renders the blocking message + Update inventory CTA when the wizard has
 * nothing to offer (FR-019). The CTA wires to `useRefreshInventory`.
 */
import { motion } from "framer-motion";
import { CloudOff, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useRefreshInventory } from "@/api/inventory";
import { strings } from "@/strings";

export function EmptyInventoryState() {
  const refresh = useRefreshInventory();
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
          <Button
            onClick={() => refresh.mutate()}
            disabled={refresh.isPending}
            className="mt-2 gap-2"
          >
            <RefreshCw
              className={
                refresh.isPending ? "h-4 w-4 animate-spin" : "h-4 w-4"
              }
            />
            {refresh.isPending
              ? strings.inventory.refreshing
              : strings.inventory.refreshButton}
          </Button>
        </CardContent>
      </Card>
    </motion.div>
  );
}
