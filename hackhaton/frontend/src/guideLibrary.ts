import type { CheckCategory } from "@/api/schemas";

export interface GuideCatalogEntry {
  id: string;
  category: CheckCategory;
  ve: boolean;
  ts: boolean;
}

export const GUIDE_CATALOG: GuideCatalogEntry[] = [
  // --- CAN Buses (VE) ---
  { id: "can_bus_overview",                 category: "communication",   ve: true,  ts: false },
  { id: "main_can_bus_reachable",           category: "communication",   ve: true,  ts: true  },
  { id: "xcp_can_bus",                      category: "communication",   ve: true,  ts: false },
  { id: "sci_can_bus",                      category: "communication",   ve: true,  ts: false },
  { id: "body_can_bus",                     category: "communication",   ve: true,  ts: false },
  { id: "chassis_can_bus",                  category: "communication",   ve: true,  ts: false },
  { id: "powertrain_can_bus",               category: "communication",   ve: true,  ts: false },
  { id: "diag_can_bus",                     category: "communication",   ve: true,  ts: false },
  { id: "depb_can_bus",                     category: "communication",   ve: true,  ts: false },

  // --- CAN Buses (TS) ---
  { id: "ts_xcp_can",                       category: "communication",   ve: false, ts: true  },
  { id: "ts_sci_can",                       category: "communication",   ve: false, ts: true  },

  // --- Network (both) ---
  { id: "network_addresses_reachable",      category: "communication",   ve: true,  ts: true  },
  { id: "network",                          category: "communication",   ve: true,  ts: true  },
  { id: "peplink_cellular_connected",       category: "communication",   ve: true,  ts: true  },
  { id: "peplink_vpn_tunnels_established",  category: "communication",   ve: true,  ts: true  },

  // --- Hardware (VE) ---
  { id: "reecu_wake_line_active",           category: "hardware",        ve: true,  ts: false },
  { id: "front_camera",                     category: "hardware",        ve: true,  ts: true  },
  { id: "expected_front_camera_connected",  category: "hardware",        ve: true,  ts: true  },
  { id: "left_camera",                      category: "hardware",        ve: true,  ts: true  },
  { id: "expected_left_camera_connected",   category: "hardware",        ve: true,  ts: true  },
  { id: "right_camera",                     category: "hardware",        ve: true,  ts: true  },
  { id: "expected_right_camera_connected",  category: "hardware",        ve: true,  ts: true  },

  // --- Hardware (TS) ---
  { id: "ts_estop_circuit",                 category: "hardware",        ve: false, ts: true  },
  { id: "ts_integration_harness",           category: "hardware",        ve: false, ts: true  },
  { id: "ts_power_supply",                  category: "hardware",        ve: false, ts: true  },
  { id: "display_surface_reachable",        category: "hardware",        ve: false, ts: true  },
  { id: "display_surface",                  category: "hardware",        ve: false, ts: true  },
  { id: "expected_input_devices_connected", category: "hardware",        ve: false, ts: true  },
  { id: "input_devices",                    category: "hardware",        ve: false, ts: true  },

  // --- Configuration ---
  { id: "vehicle_integration_config_valid", category: "configuration",   ve: true,  ts: false },
  { id: "vehicle_config",                   category: "configuration",   ve: true,  ts: false },
  { id: "telestation_config_valid",         category: "configuration",   ve: false, ts: true  },
  { id: "telestation_config",              category: "configuration",   ve: false, ts: true  },
];

export const CATEGORY_ORDER: CheckCategory[] = [
  "communication",
  "hardware",
  "configuration",
  "software",
  "calibration",
];
