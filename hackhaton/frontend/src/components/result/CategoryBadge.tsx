/**
 * CategoryBadge (T065).
 *
 * Small coloured badge with an icon next to the item name on each row, so the
 * operator can scan for "Communication / Hardware / Configuration" at a glance
 * (FR-010).
 */
import {
  Cpu,
  Gauge,
  Package,
  Radio,
  SlidersHorizontal,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { CheckCategory } from "@/api/schemas";
import { categoryLabel } from "@/strings";
import { cn } from "@/lib/utils";

// 002 / FR-006 — five-category palette. Software covers vDrive
// manifest drift / firmware / gateware / container status; Calibration
// covers SAS calibration + GNSS yaw-rate watchdog.
const ICONS: Record<CheckCategory, LucideIcon> = {
  communication: Radio,
  hardware: Cpu,
  configuration: SlidersHorizontal,
  software: Package,
  calibration: Gauge,
};

const STYLES: Record<CheckCategory, string> = {
  communication: "border-sky-400/30 bg-sky-400/10 text-sky-300",
  hardware: "border-violet-400/30 bg-violet-400/10 text-violet-300",
  configuration: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
  software: "border-fuchsia-400/30 bg-fuchsia-400/10 text-fuchsia-300",
  calibration: "border-amber-400/30 bg-amber-400/10 text-amber-300",
};

interface CategoryBadgeProps {
  category: CheckCategory;
  className?: string;
}

export function CategoryBadge({ category, className }: CategoryBadgeProps) {
  const Icon = ICONS[category];
  return (
    <Badge
      variant="outline"
      className={cn(
        "gap-1 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider",
        STYLES[category],
        className,
      )}
    >
      <Icon className="h-3 w-3" />
      {categoryLabel(category)}
    </Badge>
  );
}
