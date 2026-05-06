/**
 * Wizard step 3 (T045) — telestation-only city picker.
 *
 * Hidden when the type step is "vehicle" (FR-001a); the picker page is
 * responsible for skipping it.
 */
import { motion } from "framer-motion";
import { MapPin } from "lucide-react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { cityLabel, strings } from "@/strings";

interface CityStepProps {
  value: string | null;
  cities: string[]; // city codes
  onSelect: (city: string) => void;
}

export function CityStep({ value, cities, onSelect }: CityStepProps) {
  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          {strings.wizard.city.title}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {strings.wizard.city.subtitle}
        </p>
      </header>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {cities.map((code, idx) => {
          const selected = value === code;
          return (
            <motion.button
              key={code}
              type="button"
              onClick={() => onSelect(code)}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.32, delay: idx * 0.04, ease: [0.16, 1, 0.3, 1] }}
              whileHover={{ y: -1 }}
              whileTap={{ scale: 0.98 }}
              className="text-left focus:outline-none"
              aria-pressed={selected}
            >
              <Card
                className={cn(
                  "glass flex items-center gap-3 p-4 transition-all",
                  selected
                    ? "border-primary/60 ring-2 ring-primary/40"
                    : "hover:border-primary/30",
                )}
              >
                <div className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-primary/10 text-primary ring-1 ring-primary/20">
                  <MapPin className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-sm font-semibold">{cityLabel(code)}</div>
                  <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
                    {code}
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
