/**
 * ChannelToggle (T041).
 *
 * A / B / both segmented control. The backend's `LiveFilter.channel`
 * mirrors this — `both` is the default and corresponds to the desktop
 * tool's two-channel view.
 *
 * Stylistically, this is a three-position toggle group built from
 * native buttons; the rest of the app uses the same pattern for
 * compact mode toggles, so we don't pull in `@radix-ui/react-toggle-group`
 * just for this.
 */
import { cn } from "@/lib/utils";

type Channel = "A" | "B" | "both";

interface ChannelToggleProps {
  value: Channel;
  onChange: (channel: Channel) => void;
}

const OPTIONS: { value: Channel; label: string }[] = [
  { value: "both", label: "Both" },
  { value: "A", label: "Ch A" },
  { value: "B", label: "Ch B" },
];

export function ChannelToggle({ value, onChange }: ChannelToggleProps) {
  return (
    <div
      role="radiogroup"
      aria-label="Channel filter"
      className="inline-flex rounded-md border bg-card/40 p-0.5"
    >
      {OPTIONS.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(opt.value)}
            className={cn(
              "rounded-sm px-3 py-1 text-xs font-medium transition-colors",
              active
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

export type { Channel };
