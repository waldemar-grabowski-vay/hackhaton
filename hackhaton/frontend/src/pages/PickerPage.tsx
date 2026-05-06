/**
 * PickerPage (T047).
 *
 * Wizard state machine: Country → Type → (City if telestation) → Host. Back
 * navigation preserves earlier choices (FR-001a). Empty / failed inventory
 * states are rendered before the wizard.
 */
import { AnimatePresence } from "framer-motion";
import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError } from "@/api/client";
import { useInventory } from "@/api/inventory";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { CityStep } from "@/components/wizard/CityStep";
import { CountryStep } from "@/components/wizard/CountryStep";
import { HostStep } from "@/components/wizard/HostStep";
import { TypeStep } from "@/components/wizard/TypeStep";
import { EmptyInventoryState } from "@/components/states/EmptyInventoryState";
import { InventoryFreshness } from "@/components/chrome/InventoryFreshness";
import { PageTransition } from "@/components/motion/PageTransition";
import { strings } from "@/strings";
import type { Country, HostType } from "@/api/schemas";

type StepKey = "country" | "type" | "city" | "host";

export function PickerPage() {
  const navigate = useNavigate();
  const inventory = useInventory();

  const [country, setCountry] = useState<Country | null>(null);
  const [type, setType] = useState<HostType | null>(null);
  const [city, setCity] = useState<string | null>(null);
  const [hostId, setHostId] = useState<string | null>(null);
  const [step, setStep] = useState<StepKey>("country");
  const [direction, setDirection] = useState<"forward" | "backward">("forward");

  // Reset later choices when an earlier step changes.
  useEffect(() => {
    setType(null);
    setCity(null);
    setHostId(null);
  }, [country]);
  useEffect(() => {
    setCity(null);
    setHostId(null);
  }, [type]);
  useEffect(() => {
    setHostId(null);
  }, [city]);

  const hosts = inventory.data?.hosts ?? [];

  const availableCountries = useMemo(() => {
    const set = new Set<Country>();
    hosts.forEach((h) => set.add(h.country));
    return Array.from(set).sort();
  }, [hosts]);

  const availableTypes = useMemo<HostType[]>(() => {
    if (!country) return [];
    const set = new Set<HostType>();
    hosts.filter((h) => h.country === country).forEach((h) => set.add(h.type));
    return Array.from(set).sort();
  }, [hosts, country]);

  const availableCities = useMemo(() => {
    if (!country || type !== "telestation") return [];
    const set = new Set<string>();
    hosts
      .filter((h) => h.country === country && h.type === "telestation" && h.city)
      .forEach((h) => h.city && set.add(h.city));
    return Array.from(set).sort();
  }, [hosts, country, type]);

  const filteredHosts = useMemo(() => {
    if (!country || !type) return [];
    return hosts
      .filter((h) => h.country === country && h.type === type)
      .filter((h) => (type === "telestation" ? h.city === city : true))
      .sort((a, b) => a.display_name.localeCompare(b.display_name));
  }, [hosts, country, type, city]);

  function goForward(next: StepKey) {
    setDirection("forward");
    setStep(next);
  }
  function goBackward(prev: StepKey) {
    setDirection("backward");
    setStep(prev);
  }

  function handleCountrySelect(value: Country) {
    setCountry(value);
    goForward("type");
  }

  function handleTypeSelect(value: HostType) {
    setType(value);
    goForward(value === "telestation" ? "city" : "host");
  }

  function handleCitySelect(value: string) {
    setCity(value);
    goForward("host");
  }

  function handleHostSelect(value: string) {
    setHostId(value);
  }

  function handleBack() {
    if (step === "host") {
      goBackward(type === "telestation" ? "city" : "type");
      return;
    }
    if (step === "city") {
      goBackward("type");
      return;
    }
    if (step === "type") {
      goBackward("country");
      return;
    }
  }

  function handleRun() {
    if (!hostId) return;
    navigate(`/host/${hostId}?run=1`);
  }

  if (inventory.isLoading) {
    return (
      <div className="mx-auto max-w-xl">
        <Card className="glass">
          <CardContent className="flex items-center justify-center gap-3 p-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading inventory…
          </CardContent>
        </Card>
      </div>
    );
  }

  const inventoryUnavailable =
    inventory.error instanceof ApiError &&
    inventory.error.code === "inventory_unavailable";
  if (inventoryUnavailable || (inventory.data && inventory.data.hosts.length === 0)) {
    return <EmptyInventoryState />;
  }

  if (inventory.isError) {
    return (
      <div className="mx-auto max-w-xl">
        <Card className="glass">
          <CardContent className="space-y-2 p-6 text-sm">
            <div className="font-semibold">Couldn't load the host list</div>
            <div className="text-muted-foreground">{strings.errors.network}</div>
            <Button onClick={() => inventory.refetch()} className="mt-2">
              Try again
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!inventory.data) return null;

  const stepIndex =
    step === "country" ? 1 : step === "type" ? 2 : step === "city" ? 3 : 4;
  const totalSteps = type === "vehicle" ? 3 : 4;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-xs uppercase tracking-wider text-muted-foreground">
          {strings.wizard.progressLabel} {Math.min(stepIndex, totalSteps)} of{" "}
          {totalSteps}
        </div>
        <InventoryFreshness meta={inventory.data.meta} />
      </div>

      {/* progress bar */}
      <div className="flex h-1 overflow-hidden rounded-full bg-card/50">
        {Array.from({ length: totalSteps }).map((_, i) => {
          const active = i < stepIndex;
          return (
            <div
              key={i}
              className={
                active
                  ? "flex-1 bg-gradient-to-r from-primary to-accent"
                  : "flex-1 bg-transparent"
              }
              style={{ marginRight: i < totalSteps - 1 ? 4 : 0 }}
            />
          );
        })}
      </div>

      <AnimatePresence mode="wait" custom={direction}>
        {step === "country" && (
          <PageTransition motionKey="country" direction={direction}>
            <CountryStep
              value={country}
              available={availableCountries}
              onSelect={handleCountrySelect}
            />
          </PageTransition>
        )}
        {step === "type" && (
          <PageTransition motionKey="type" direction={direction}>
            <TypeStep
              value={type}
              available={availableTypes}
              onSelect={handleTypeSelect}
            />
          </PageTransition>
        )}
        {step === "city" && (
          <PageTransition motionKey="city" direction={direction}>
            <CityStep value={city} cities={availableCities} onSelect={handleCitySelect} />
          </PageTransition>
        )}
        {step === "host" && (
          <PageTransition motionKey="host" direction={direction}>
            <HostStep value={hostId} hosts={filteredHosts} onSelect={handleHostSelect} />
          </PageTransition>
        )}
      </AnimatePresence>

      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
        <Button
          variant="ghost"
          onClick={handleBack}
          disabled={step === "country"}
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          {strings.wizard.backButton}
        </Button>
        {step === "host" && (
          <Button
            onClick={handleRun}
            disabled={!hostId}
            size="lg"
            className="gap-2 bg-gradient-to-r from-primary to-accent text-primary-foreground shadow-[0_8px_24px_-12px_hsl(var(--primary)/0.7)] hover:opacity-95"
          >
            {strings.runs.runButton}
            <ArrowRight className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
