/**
 * Single source of truth for every operator-visible string in v1 (FR-014, R6).
 *
 * Constitution Principle III: this file is the entire surface a reviewer must
 * audit for operator-facing jargon. Keep all human-readable strings here.
 */

export const strings = {
  app: {
    name: "VayOBD",
    tagline: "Remote host diagnostics",
  },
  wizard: {
    backButton: "Back",
    progressLabel: "Step",
    country: {
      title: "Where is the host?",
      subtitle: "Pick the country to narrow down what you're checking.",
      de: "Germany",
    },
    type: {
      title: "What are you checking?",
      subtitle: "Vehicle for a remote drive system, telestation for a control room.",
      vehicle: "Vehicle",
      vehicleHint: "Driverless vehicle (Apollo, Loki, etc.)",
      telestation: "Telestation",
      telestationHint: "Operator console at a control centre",
    },
    city: {
      title: "Which city?",
      subtitle: "Pick the city the telestation is in.",
    },
    host: {
      title: "Pick a host",
      subtitle: "Each tile is one machine you can run a check against.",
    },
    runButton: "Run check",
  },
  cities: {
    ber: "Berlin",
  } as Record<string, string>,
  countries: {
    de: "Germany",
  } as Record<string, string>,
  inventory: {
    empty: {
      title: "We couldn't load the host list",
      body: "Try updating the inventory to fetch the latest hosts.",
    },
    refreshButton: "Update inventory",
    refreshing: "Updating…",
    refreshFailedToast: {
      title: "Inventory update failed",
      body: "We kept the previous list. Check your connection and try again.",
    },
    lastRefreshedPrefix: "Updated",
  },
  runs: {
    runButton: "Run check",
    runAgainButton: "Run check again",
    inProgress: "Running checks against",
    inProgressShort: "Running checks…",
    inProgressDetail: "We're talking to the host. This usually takes a few seconds.",
    inProgressTakingLonger: "Still running — this is taking longer than usual.",
    inProgressToastTitle: "A check is already running",
    inProgressToastBody: "Hold on — we'll show the result as soon as it finishes.",
    unknownHost: {
      title: "Host not found",
      body: "This host isn't in the current inventory. Try updating the inventory.",
    },
    noneYet: {
      title: "No previous run",
      body: "Pick a host from the wizard and run your first check.",
    },
  },
  outcomes: {
    complete: {
      headline: "All checks passed",
      subline: "Every item is reporting healthy.",
    },
    completeWithErrors: {
      headline: "Some items need attention",
      subline: "Follow the suggested next steps to get this host back to healthy.",
    },
    partial: {
      headline: "Run finished partially",
      body: "Some checks didn't return a result. The visible items below are still useful.",
    },
    unreachable: {
      title: "We couldn't reach this host",
      body: "The host didn't answer. Confirm it's powered on, on the network, and try again.",
    },
    timeout: {
      title: "Check took too long",
      body: "The host didn't finish in time. Try again — if it keeps happening, the host may be slow or stuck.",
    },
  },
  result: {
    workingHeading: "Working",
    needsAttentionHeading: "Needs attention",
    workingCount_one: "1 item",
    workingCount_other: "{count} items",
    rawDetailToggleShow: "Show raw output",
    rawDetailToggleHide: "Hide raw output",
    rawDetailEmpty: "No raw output captured.",
    rawDetailLabel: "Raw output",
    timestampPrefix: "Checked",
    timestampJustNow: "just now",
    backToWizard: "Pick another host",
    runStartedAt: "Run started",
  },
  category: {
    communication: "Communication",
    hardware: "Hardware",
    configuration: "Configuration",
  },
  errors: {
    generic:
      "Something went wrong. Try again, and update the inventory if the problem persists.",
    network:
      "We couldn't reach the diagnostics service. Check your connection and try again.",
  },
  // Per-item operator-visible names + descriptions + recommended actions.
  // Keys mirror catalog.py / data-model.md item ids.
  item: {
    main_can_bus_reachable: {
      name: "Main CAN bus reachable",
    },
    front_camera: {
      description: {
        working: "Front camera is connected and recognised.",
        error: "We couldn't see the front camera on the USB bus.",
      },
      action:
        "Re-seat the front camera USB cable, then run the check again.",
    },
    left_camera: {
      description: {
        working: "Left camera is connected and recognised.",
        error: "We couldn't see the left camera on the USB bus.",
      },
      action:
        "Re-seat the left camera USB cable, then run the check again.",
    },
    right_camera: {
      description: {
        working: "Right camera is connected and recognised.",
        error: "We couldn't see the right camera on the USB bus.",
      },
      action:
        "Re-seat the right camera USB cable, then run the check again.",
    },
    expected_front_camera_connected: {
      name: "Front camera connected",
    },
    expected_left_camera_connected: {
      name: "Left camera connected",
    },
    expected_right_camera_connected: {
      name: "Right camera connected",
    },
    vehicle_integration_config_valid: {
      name: "Vehicle configuration valid",
    },
    vehicle_config: {
      description: {
        working: "Vehicle configuration is present and well-formed.",
        error: "Vehicle configuration is missing or has an unexpected shape.",
      },
      action:
        "Re-deploy the vehicle config from ree-vehicle-configs and re-run.",
    },
    network_addresses_reachable: {
      name: "Network reachable",
    },
    network: {
      description: {
        working: "Vehicle's expected network addresses respond.",
        error: "One or more vehicle network addresses didn't respond.",
      },
      action:
        "Confirm the vehicle is online and on the expected network, then re-run.",
    },
    display_surface_reachable: {
      name: "Display surface reachable",
    },
    display_surface: {
      description: {
        working: "Operator display is responding.",
        error: "Operator display didn't respond on the expected port.",
      },
      action:
        "Confirm the display server is running on this telestation and re-run.",
    },
    expected_input_devices_connected: {
      name: "Input devices connected",
    },
    input_devices: {
      description: {
        working: "Expected input devices are connected.",
        error: "Expected input devices are missing.",
      },
      action:
        "Re-seat the steering wheel / pedals and confirm power, then re-run.",
    },
    telestation_config_valid: {
      name: "Telestation configuration valid",
    },
    telestation_config: {
      description: {
        working: "Telestation configuration is present and well-formed.",
        error: "Telestation configuration is missing or has an unexpected shape.",
      },
      action:
        "Re-deploy the telestation config from ree-vehicle-configs and re-run.",
    },
  },
} as const;

export type StringPath = string;

/**
 * `t("inventory.empty.title")` — dot-path lookup. Returns the path itself when
 * the key is missing so a missing copy is loud, not silent. A future i18n pass
 * can swap this implementation without touching call sites.
 */
export function t(path: StringPath | null | undefined): string {
  if (!path) return "";
  const segments = path.split(".");
  let current: unknown = strings;
  for (const segment of segments) {
    if (typeof current !== "object" || current === null) return path;
    current = (current as Record<string, unknown>)[segment];
  }
  return typeof current === "string" ? current : path;
}

export function cityLabel(code: string | null | undefined): string {
  if (!code) return "";
  return strings.cities[code] ?? code.toUpperCase();
}

export function countryLabel(code: string): string {
  return strings.countries[code] ?? code.toUpperCase();
}

export function categoryLabel(category: string): string {
  return (strings.category as Record<string, string>)[category] ?? category;
}

export function prettyHostName(displayName: string, type: string): string {
  // Friendly-cap bare lowercase names ("apollo" → "Apollo"); leave numeric ids alone.
  if (/^[0-9]/.test(displayName)) {
    return type === "vehicle" ? `Vehicle ${displayName}` : `Telestation ${displayName}`;
  }
  return displayName.charAt(0).toUpperCase() + displayName.slice(1);
}
