/**
 * Wizard step 1 (T043, FR-001a step 1, Clarification 2026-05-07).
 *
 * Renders Germany (selectable) plus a static "United States — Coming soon"
 * tile that is disabled and does not advance the wizard. The US tile has
 * no backing inventory data on the wire (the loader filters non-DE hosts
 * at load time); it is purely a UI signal that US support is on the
 * near-term roadmap.
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

interface Tile {
  code: "de" | "us";
  label: string;
  flag: string;
  disabled: boolean;
  badge?: string;
}

const TILES: Tile[] = [
  { code: "de", label: strings.wizard.country.de, flag: "🇩🇪", disabled: false },
  {
    code: "us",
    label: strings.wizard.country.us,
    flag: "🇺🇸",
    disabled: true,
    badge: strings.wizard.country.usDisabled,
  },
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
        {TILES.map((tile, idx) => {
          const selected = !tile.disabled && value === tile.code;
          // The DE tile is also gated on the inventory actually containing DE
          // hosts — without that, we shouldn't let the operator advance into
          // an empty type step.
          const enabled = !tile.disabled && available.includes(tile.code as "de");
          const handleClick = () => {
            if (!enabled) return;
            onSelect(tile.code as "de");
          };
          return (
            <motion.button
              key={tile.code}
              type="button"
              onClick={handleClick}
              disabled={!enabled}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.36, delay: idx * 0.06, ease: [0.16, 1, 0.3, 1] }}
              whileHover={enabled ? { y: -2 } : undefined}
              whileTap={enabled ? { scale: 0.985 } : undefined}
              className={cn(
                "text-left focus:outline-none",
                !enabled && "cursor-not-allowed",
              )}
              aria-pressed={selected}
              aria-disabled={!enabled}
              data-disabled={!enabled || undefined}
              data-country={tile.code}
            >
              <Card
                className={cn(
                  "glass relative overflow-hidden p-6 transition-all",
                  selected
                    ? "border-primary/60 ring-2 ring-primary/40"
                    : enabled
                      ? "hover:border-primary/30"
                      : "opacity-60 grayscale",
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
                {tile.badge && (
                  <div className="absolute right-3 top-3 rounded-full border border-border/60 bg-background/60 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    {tile.badge}
                  </div>
                )}
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
