/**
 * Wizard step 2 (T044) — Vehicle / Telestation card picker.
 */
import { motion } from "framer-motion";
import { Car, Monitor } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { strings } from "@/strings";

interface TypeStepProps {
  value: "vehicle" | "telestation" | null;
  available: ("vehicle" | "telestation")[];
  onSelect: (type: "vehicle" | "telestation") => void;
}

const TILES: {
  code: "vehicle" | "telestation";
  label: string;
  hint: string;
  icon: LucideIcon;
}[] = [
  {
    code: "vehicle",
    label: strings.wizard.type.vehicle,
    hint: strings.wizard.type.vehicleHint,
    icon: Car,
  },
  {
    code: "telestation",
    label: strings.wizard.type.telestation,
    hint: strings.wizard.type.telestationHint,
    icon: Monitor,
  },
];

export function TypeStep({ value, available, onSelect }: TypeStepProps) {
  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          {strings.wizard.type.title}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {strings.wizard.type.subtitle}
        </p>
      </header>
      <div className="grid gap-4 sm:grid-cols-2">
        {TILES.filter((t) => available.includes(t.code)).map((tile, idx) => {
          const selected = value === tile.code;
          const Icon = tile.icon;
          return (
            <motion.button
              key={tile.code}
              type="button"
              onClick={() => onSelect(tile.code)}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.36, delay: idx * 0.06, ease: [0.16, 1, 0.3, 1] }}
              whileHover={{ y: -2 }}
              whileTap={{ scale: 0.985 }}
              className="text-left focus:outline-none"
              aria-pressed={selected}
            >
              <Card
                className={cn(
                  "glass h-full overflow-hidden p-6 transition-all",
                  selected
                    ? "border-primary/60 ring-2 ring-primary/40"
                    : "hover:border-primary/30",
                )}
              >
                <div className="flex items-start gap-4">
                  <div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="text-lg font-semibold">{tile.label}</div>
                    <div className="mt-0.5 text-sm text-muted-foreground">
                      {tile.hint}
                    </div>
                  </div>
                </div>
              </Card>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
