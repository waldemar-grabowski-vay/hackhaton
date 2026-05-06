/**
 * Wizard step 1 (T043) — country tile picker. v1 ships Germany only.
 */
import { motion } from "framer-motion";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { strings } from "@/strings";

interface CountryStepProps {
  value: "de" | null;
  available: "de"[];
  onSelect: (country: "de") => void;
}

const TILES: { code: "de"; label: string; flag: string }[] = [
  { code: "de", label: strings.wizard.country.de, flag: "🇩🇪" },
];

export function CountryStep({ value, available, onSelect }: CountryStepProps) {
  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          {strings.wizard.country.title}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {strings.wizard.country.subtitle}
        </p>
      </header>
      <div className="grid gap-4 sm:grid-cols-2">
        {TILES.filter((t) => available.includes(t.code)).map((tile, idx) => {
          const selected = value === tile.code;
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
                  "glass relative overflow-hidden p-6 transition-all",
                  selected
                    ? "border-primary/60 ring-2 ring-primary/40"
                    : "hover:border-primary/30",
                )}
              >
                <div className="flex items-center gap-4">
                  <div className="text-5xl leading-none">{tile.flag}</div>
                  <div>
                    <div className="text-lg font-semibold">{tile.label}</div>
                    <div className="text-xs uppercase tracking-wider text-muted-foreground">
                      {tile.code.toUpperCase()}
                    </div>
                  </div>
                </div>
                {selected && (
                  <motion.div
                    layoutId="country-pill"
                    className="absolute inset-0 -z-10 rounded-[inherit] bg-primary/8"
                  />
                )}
              </Card>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
