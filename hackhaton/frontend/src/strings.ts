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
    continueButton: "Continue",
    progressLabel: "Step",
    country: {
      title: "Where is the host?",
      subtitle: "Pick the country to narrow down what you're checking.",
      de: "Germany",
      us: "United States",
      usDisabled: "Coming soon",
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
    refreshFailedBanner: {
      title: "Inventory updates are failing",
      body: "We're still using the last good copy. The host list may be out of date.",
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
      title: "Ready when you are",
      body: "Click Run check to start the diagnostic against this host.",
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
      title: "Host is offline",
      body: "The host didn't answer. Follow the troubleshooting steps below to restore connectivity.",
    },
    timeout: {
      title: "Check timed out",
      body: "The host didn't respond in time. It may be overloaded or stuck — follow the steps below.",
    },
    offlineReasons: {
      network_unreachable: "Network unreachable",
      ssh_auth_failed: "SSH authentication failed",
      ssh_timeout: "SSH connection timed out",
      service_unresponsive: "Diagnostic service not responding",
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
  // 002 / FR-006 — five-category palette. Software covers vDrive
  // manifest drift / firmware / gateware / container status;
  // Calibration covers SAS calibration + GNSS yaw-rate watchdog.
  category: {
    communication: "Communication",
    hardware: "Hardware",
    configuration: "Configuration",
    software: "Software",
    calibration: "Calibration",
  },
  errors: {
    generic:
      "Something went wrong. Try again, and update the inventory if the problem persists.",
    network:
      "We couldn't reach the diagnostics service. Check your connection and try again.",
    unauthenticated:
      "We couldn't confirm who you are. Sign in through Vay corporate SSO and try again.",
  },
  guide: {
    viewButton: "View repair guide",
    noGuideTitle: "No repair guide available",
    noGuideBody: "Follow the suggested next step above, or contact the engineering team for assistance.",
    debugHeading: "Debug suggestions",
    stepPhysical: "Physical action",
    closeButton: "Close",
  },
  // Per-item operator-visible names + descriptions + recommended actions.
  // Keys mirror catalog.py / data-model.md item ids.
  item: {
    main_can_bus_reachable: {
      name: "Main CAN bus reachable",
      description: {
        working: "APP CAN bus is up and receiving frames.",
        error: "No frames detected on the APP CAN bus.",
      },
      action: "Re-seat the Integration Harness connectors and re-run the check.",
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
    reecu_wake_line_active: {
      name: "REECU WAKE line active",
    },
    reecu_wake_line: {
      description: {
        working: "KL15 WAKE signal on REECU connector X9 is present (12 V).",
        error: "KL15 WAKE signal on REECU connector X9 is absent or below threshold.",
      },
      action:
        "Inspect the WAKE line on connector X9 pin 1. Check the KL15 fuse and the Integration harness.",
    },
    peplink_cellular_connected: {
      name: "Peplink cellular connected",
    },
    peplink_vpn_tunnels_established: {
      name: "Peplink VPN tunnels established",
    },
    peplink_cellular: {
      description: {
        working: "All Peplink cellular interfaces are connected and reporting green.",
        error: "One or more Peplink cellular interfaces are not reporting green.",
      },
      action:
        "Check antenna connections and SIM card seats on the Peplink router, then re-run.",
    },
    peplink_vpn: {
      description: {
        working: "All 5 PepVPN tunnels are established.",
        error: "Not all 5 expected PepVPN tunnels are established.",
      },
      action:
        "Check the Peplink router WAN connection and VPN configuration, then re-run.",
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
