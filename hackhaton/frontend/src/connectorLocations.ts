export type ConnectorLocation = { fx: number; fy: number };

export type VehicleHarnessKey =
  | "board"
  | "vih"
  | "apcb"
  | "accessory"
  | "ipdu"
  | "center_console"
  | "pigtail_m40"
  | "hood_pdu"
  | "pdu_system"
  | "pdu"
  | "steering"
  | "kiafusebox"
  | "estop_loopback"
  | "depb_extension"
  | "wl_gnd";

export const HARNESS_IMAGES: Record<VehicleHarnessKey, string> = {
  board:           "/harness-diagram.png",
  vih:             "/ve-vih-harness.png",
  apcb:            "/ve-apcb-harness.png",
  accessory:       "/ve-accessory-harness.png",
  ipdu:            "/ve-ipdu-harness.png",
  center_console:  "/ve-center-console-harness.png",
  pigtail_m40:     "/ve-pigtail-m40-harness.png",
  hood_pdu:        "/ve-hood-pdu-harness.png",
  pdu_system:      "/ve-pdu-system-harness.png",
  pdu:             "/ve-pdu-harness.png",
  steering:        "/ve-steering-harness.png",
  kiafusebox:      "/ve-kiafusebox-harness.png",
  estop_loopback:  "/ve-estop-loopback-harness.png",
  depb_extension:  "/ve-depb-extension-harness.png",
  wl_gnd:          "/ve-wl-gnd-harness.png",
};

export const HARNESS_LABELS: Record<VehicleHarnessKey, string> = {
  board:           "Board",
  vih:             "VIH",
  apcb:            "APCB",
  accessory:       "Accessory",
  ipdu:            "IPDU",
  center_console:  "Center Console",
  pigtail_m40:     "Pigtail M40",
  hood_pdu:        "Hood→PDU",
  pdu_system:      "PDU→System",
  pdu:             "PDU",
  steering:        "Steering",
  kiafusebox:      "KIA Fusebox",
  estop_loopback:  "E-Stop Loop",
  depb_extension:  "DEPB Ext",
  wl_gnd:          "WL-GND",
};

export const HARNESS_ORDER: VehicleHarnessKey[] = [
  "board",
  "vih",
  "apcb",
  "accessory",
  "ipdu",
  "center_console",
  "pigtail_m40",
  "hood_pdu",
  "pdu",
  "pdu_system",
  "steering",
  "kiafusebox",
  "estop_loopback",
  "depb_extension",
  "wl_gnd",
];

/** Connector ID → which harness image it lives on (always board for chip-click focus) */
export const CONNECTOR_HARNESS: Record<string, VehicleHarnessKey> = {
  VIH_2_REEBOX_F: "board",
  CREECU_0:       "board",
  CREECU_1:       "board",
  REECU_X9:       "board",
  CREECU_X9:      "board",
  K15_Fuse:       "board",
  PDU_System:     "board",
  Reebox_Main_M:  "board",
  Reebox_Main_F:  "board",
  APCB_2_VIH:     "board",
};

// Fractional (0–1) positions within each harness PNG.
// Calibrate by overlaying the PNG at 100% and measuring connector label centres.
export const vehicleConnectorLocations: Record<VehicleHarnessKey, Record<string, ConnectorLocation>> = {
  board: {
    CREECU_0:       { fx: 0.450, fy: 0.229 },
    CREECU_1:       { fx: 0.453, fy: 0.232 },
    REECU_X9:       { fx: 0.448, fy: 0.226 },
    CREECU_X9:      { fx: 0.452, fy: 0.228 },
    K15_Fuse:       { fx: 0.327, fy: 0.183 },
    PDU_System:     { fx: 0.553, fy: 0.104 },
    APCB_2_VIH:     { fx: 0.380, fy: 0.311 },
    VIH_2_REEBOX_F: { fx: 0.673, fy: 0.335 },
    Reebox_Main_F:  { fx: 0.575, fy: 0.613 },
    Reebox_Main_M:  { fx: 0.608, fy: 0.615 },
  },
  vih:            { VIH_2_REEBOX_F: { fx: 0.50, fy: 0.50 } },
  apcb:           { APCB_2_VIH: { fx: 0.50, fy: 0.50 } },
  accessory:      { Reebox_Main_F: { fx: 0.50, fy: 0.50 }, Reebox_Main_M: { fx: 0.50, fy: 0.50 } },
  ipdu:           {},
  center_console: {},
  pigtail_m40:    {},
  hood_pdu:       {},
  pdu_system:     {},
  pdu:            {},
  steering:       {},
  kiafusebox:     {},
  estop_loopback: {},
  depb_extension: {},
  wl_gnd:         {},
};

/** Flat map kept for any legacy callers */
export const connectorLocations: Record<string, ConnectorLocation> = Object.fromEntries(
  (Object.values(vehicleConnectorLocations) as Record<string, ConnectorLocation>[])
    .flatMap((locs) => Object.entries(locs)),
);
