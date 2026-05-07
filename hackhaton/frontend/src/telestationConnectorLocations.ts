export type ConnectorLocation = { fx: number; fy: number };

export type HarnessKey =
  | "board"
  | "rdms"
  | "integration"
  | "steering"
  | "power"
  | "estop"
  | "acdc_eu"
  | "acdc_us";

export const HARNESS_IMAGES: Record<HarnessKey, string> = {
  board:        "/ts-board.png",
  rdms:         "/ts-rdms-harness.png",
  integration:  "/ts-integration-harness.png",
  steering:     "/ts-steering-harness.png",
  power:        "/ts-power-harness.png",
  estop:        "/ts-estop-harness.png",
  acdc_eu:      "/ts-acdc-eu-harness.png",
  acdc_us:      "/ts-acdc-us-harness.png",
};

export const HARNESS_LABELS: Record<HarnessKey, string> = {
  board:        "Board",
  rdms:         "RDMS",
  integration:  "Integration",
  steering:     "Steering",
  power:        "Power",
  estop:        "E-Stop",
  acdc_eu:      "AC/DC EU",
  acdc_us:      "AC/DC US",
};

export const HARNESS_ORDER: HarnessKey[] = [
  "board",
  "rdms",
  "integration",
  "steering",
  "power",
  "estop",
  "acdc_eu",
  "acdc_us",
];

/** Connector ID → which harness it lives on */
export const CONNECTOR_HARNESS: Record<string, HarnessKey> = {
  REECU_X9:      "integration",
  CREECU_X9:     "integration",
  REECU_X4:      "integration",
  TIH_REECU_F:   "integration",
  TIH_Main_M:    "integration",
  TIH_Main_F:    "integration",
  SW_System_F:   "steering",
  SAS_0:         "steering",
  SAS_1:         "steering",
  Column_Left:   "steering",
  Column_Right:  "steering",
  REECU_POWER:   "power",
  E_Stop_F:      "estop",
  AC_DC_EU:      "acdc_eu",
  AC_DC_US:      "acdc_us",
};

// Fractional (0–1) positions within each harness PNG.
// Calibrate by overlaying each PNG at 100% and measuring connector label centres.
export const telestationConnectorLocations: Record<HarnessKey, Record<string, ConnectorLocation>> = {
  board: {},
  rdms: {},
  integration: {
    REECU_X9:    { fx: 0.18, fy: 0.40 },
    CREECU_X9:   { fx: 0.18, fy: 0.40 },
    REECU_X4:    { fx: 0.18, fy: 0.55 },
    TIH_REECU_F: { fx: 0.50, fy: 0.35 },
    TIH_Main_M:  { fx: 0.75, fy: 0.50 },
    TIH_Main_F:  { fx: 0.75, fy: 0.62 },
  },
  steering: {
    SW_System_F:  { fx: 0.50, fy: 0.30 },
    SAS_0:        { fx: 0.30, fy: 0.55 },
    SAS_1:        { fx: 0.70, fy: 0.55 },
    Column_Left:  { fx: 0.25, fy: 0.75 },
    Column_Right: { fx: 0.75, fy: 0.75 },
  },
  power: {
    REECU_POWER: { fx: 0.50, fy: 0.45 },
  },
  estop: {
    E_Stop_F: { fx: 0.50, fy: 0.45 },
  },
  acdc_eu: {
    AC_DC_EU: { fx: 0.50, fy: 0.45 },
  },
  acdc_us: {
    AC_DC_US: { fx: 0.50, fy: 0.45 },
  },
};
