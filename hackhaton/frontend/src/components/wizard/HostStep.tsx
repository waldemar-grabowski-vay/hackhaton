/**
 * Wizard step 4 (T046) — host card grid. Selecting a host enables the
 * "Run check" button on the picker page.
 */
import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { prettyHostName, strings } from "@/strings";
import type { Host } from "@/api/schemas";

interface HostStepProps {
  value: string | null;
  hosts: Host[];
  onSelect: (hostId: string) => void;
}

export function HostStep({ value, hosts, onSelect }: HostStepProps) {
  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          {strings.wizard.host.title}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {strings.wizard.host.subtitle}
        </p>
      </header>
      {hosts.length === 0 ? (
        <Card className="glass p-6 text-sm text-muted-foreground">
          No hosts match this combination yet.
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {hosts.map((host, idx) => {
            const selected = value === host.id;
            return (
              <motion.button
                key={host.id}
                type="button"
                onClick={() => onSelect(host.id)}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.32, delay: idx * 0.03, ease: [0.16, 1, 0.3, 1] }}
                whileHover={{ y: -1 }}
                whileTap={{ scale: 0.98 }}
                className="text-left focus:outline-none"
                aria-pressed={selected}
              >
                <Card
                  className={cn(
                    "glass group flex items-center justify-between gap-3 p-4 transition-all",
                    selected
                      ? "border-primary/60 ring-2 ring-primary/40"
                      : "hover:border-primary/30",
                  )}
                >
                  <div className="min-w-0 leading-tight">
                    <div className="truncate text-sm font-semibold">
                      {prettyHostName(host.display_name, host.type)}
                    </div>
                    <div className="mt-0.5 text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                      {host.id}
                    </div>
                  </div>
                  <ChevronRight
                    className={cn(
                      "h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5",
                      selected && "text-primary",
                    )}
                  />
                </Card>
              </motion.button>
            );
          })}
        </div>
      )}
    </div>
  );
}
