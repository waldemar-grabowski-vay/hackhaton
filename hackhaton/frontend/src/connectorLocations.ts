/** Fraction-based (0–1) position of a connector label within harness-diagram.svg */
export type ConnectorLocation = { fx: number; fy: number };

// Coordinates extracted from VayScale Hardware Configuration.svg
// SVG canvas: 22902.36 × 15268.24 px (Miro export)
// To re-calibrate: run scripts/find-connector-coords.py
export const connectorLocations: Record<string, ConnectorLocation> = {
  // Extracted from SVG text positions; PNG is 3000x4808.
  // Adjust fx/fy by small increments if the zoom lands slightly off.
  VIH_2_REEBOX_F: { fx: 0.665, fy: 0.337 },
  Reebox_Main_M:  { fx: 0.411, fy: 0.670 },
  Reebox_Main_F:  { fx: 0.411, fy: 0.670 },
  CREECU_0:       { fx: 0.150, fy: 0.500 },
  CREECU_1:       { fx: 0.155, fy: 0.510 },
  REECU_X9:       { fx: 0.150, fy: 0.490 },
  CREECU_X9:      { fx: 0.150, fy: 0.490 },
  APCB_2_VIH:     { fx: 0.145, fy: 0.522 },
  K15_Fuse:       { fx: 0.680, fy: 0.140 },
  PDU_System:     { fx: 0.680, fy: 0.140 },
};
