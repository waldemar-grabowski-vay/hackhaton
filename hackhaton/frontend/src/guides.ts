/**
 * Pre-authored repair guide catalogue (FR-008, FR-009).
 *
 * Keyed by diagnostic item ID (mirrors catalog.py / strings.ts item.*).
 * Guide content is static — bundled with the app, no network fetch required.
 * Debug suggestions are only shown in Developer mode (FR-006, FR-007).
 *
 * Harness data sourced from: VS050100 v4.5, VS101500 v4.2, VS101400 v4.5,
 * VS051800 v1.4, VS040804 v2.6, and cross-referenced PCB schematics (X7/X8/X9).
 */

import {
  APP_CAN_PATH_SVG,
  TS_APP_CAN_PATH_SVG,
  VIH_2_REEBOX_F_SVG,
  REEBOX_MAIN_F_SVG,
  WAKE_PATH_SVG,
  APCB_2_VIH_SVG,
  XCP_CAN_PATH_SVG,
  SCI_CAN_PATH_SVG,
  BODY_CAN_PATH_SVG,
  CHASSIS_CAN_PATH_SVG,
  POWERTRAIN_CAN_PATH_SVG,
  DIAG_CAN_PATH_SVG,
  DEPB_CAN_PATH_SVG,
  ESTOP_PATH_SVG,
  TIH_PATH_SVG,
  TS_POWER_PATH_SVG,
  TS_XCP_CAN_PATH_SVG,
  TS_SCI_CAN_PATH_SVG,
  IPF_F_SVG,
  EPB_M_SVG,
  E_STOP_F_SVG,
  TIH_MAIN_M_SVG,
  // new focused connector variants
  REEBOX_MAIN_F_XCP_SVG,
  REEBOX_MAIN_F_SCI_SVG,
  CIPG_F_BODY_SVG,
  CIPG_F_CHASSIS_SVG,
  CAN_BUS_OVERVIEW_SVG,
} from "@/connectorSpecs";
import { photosForPNs } from "@/connectorPhotos";

export type RepairStep = {
  title: string;
  body: string;
  physical?: true;
  connectors?: Array<{ id: string; label: string }>;
};

export type ConnectorPhoto = {
  label: string;
  url: string;
};

export type DebugSuggestion = {
  label: string;
  body: string;
  /** Inline SVG string rendered above the body text (developer mode only). */
  diagram?: string;
  /** Clickable photo links that open in a new tab — real connector images. */
  photos?: ConnectorPhoto[];
  /** Connector chips that zoom the vehicle diagram to the connector's location. */
  connectors?: Array<{ id: string; label: string }>;
};

export type RepairGuide = {
  steps: RepairStep[];
  debugSuggestions: DebugSuggestion[];
  /** If true, this guide is suppressed for telestation hosts. */
  vehicleOnly?: true;
};

export const guides: Record<string, RepairGuide> = {
  main_can_bus_reachable: {
    vehicleOnly: true,
    steps: [
      {
        title: "Confirm the REEBox is powered on",
        body: "Check that the REEBox LED indicators are lit. If the REEBox is off, check the main power cable and fuses before continuing.",
        physical: true,
      },
      {
        title: "Re-seat the Accessory harness connector at the REEBox",
        body: "Locate the Reebox_Main connector on the side of the REEBox (8-pin connector). Press the locking tab, pull it off, and push it back in firmly until it clicks.",
        physical: true,
      },
      {
        title: "Re-seat the VIH_2_REEBOX_F connector on the Vehicle Integration Harness",
        body: "Trace the cable from the REEBox Accessory connector back to the Vehicle Integration Harness. Find the VIH_2_REEBOX_F connector and re-seat it.",
        physical: true,
      },
      {
        title: "Inspect the harness for visible damage",
        body: "Visually check the cable run from the VIH to the REEBox for pinching, cuts, or loose connectors. Look for bent or pushed-back pins.",
        physical: true,
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again to confirm whether the issue is resolved.",
      },
    ],
    debugSuggestions: [
      {
        label: "Signal path",
        diagram: APP_CAN_PATH_SVG,
        body:
          "APP CAN (canonical: APP_CAN_H / APP_CAN_L)\n" +
          "REECU PCB X8 (alias CREECU_1) — REECU logical port: CAN 0 — nets REF_AUX_CAN_H / REF_AUX_CAN_L\n" +
          "→ VIH splices APP_HIGH_CAN_S / APP_LOW_CAN_S\n" +
          "→ VIH_2_REEBOX_F pin 1 (Yellow, H) & pin 2 (Gray, L)\n" +
          "→ Accessory harness Reebox_Main_F pins 1 & 2  →  IPDU Reebox_Main_M\n" +
          "NOTE: APP CAN does NOT route through VIH_2_CENTER_CONSOLE.",
      },
      {
        label: "Connector: VIH_2_REEBOX_F",
        diagram: VIH_2_REEBOX_F_SVG,
        photos: photosForPNs(["19418-0029"]),
        connectors: [{ id: "VIH_2_REEBOX_F", label: "VIH_2_REEBOX_F" }],
        body:
          "Molex 19418-0029 · 16-pin female — on the Vehicle Integration Harness (VS050100).\n" +
          "Re-seat both sides of this connector — it bridges the VIH to the REEBox path.\n" +
          "Check for bent pins, corrosion, or moisture on the mating faces.",
      },
      {
        label: "Connector: Reebox_Main_F / Reebox_Main_M",
        diagram: REEBOX_MAIN_F_SVG,
        connectors: [
          { id: "Reebox_Main_F", label: "Reebox_Main_F" },
          { id: "Reebox_Main_M", label: "Reebox_Main_M" },
        ],
        // PN not yet confirmed for Reebox_Main_F — add to photosForPNs([...]) once identified.
        body:
          "8-pin female (Accessory Harness VS101500) mates with Reebox_Main_M (IPDU VS101400).\n" +
          "Pins 1 & 2 carry APP CAN (twisted pair — Yellow / Gray).\n" +
          "Re-seat the mating pair; confirm no pin backs-out when the locking tab is released.",
      },
      {
        label: "CAN bus health check",
        body:
          "On the REECU host, inspect the CAN interface:\n" +
          "  ip -details link show canX\n" +
          "  candump canX\n" +
          "Expected: frames from APP CAN devices.\n" +
          "Bus-off / heavy TX errors → check 120 Ω termination at each end.\n" +
          "Silent bus → suspect open circuit at VIH_2_REEBOX_F.1 or .2.",
      },
      {
        label: "Splice continuity",
        body:
          "If connectors check out and the bus is still dead, measure continuity:\n" +
          "  VIH_2_REEBOX_F.1 → REECU X8 REF_AUX_CAN_H  (across APP_HIGH_CAN_S)\n" +
          "  VIH_2_REEBOX_F.2 → REECU X8 REF_AUX_CAN_L  (across APP_LOW_CAN_S)\n" +
          "Open circuit = broken splice or damaged wire inside the VIH.",
      },
    ],
  },

  front_camera: {
    steps: [
      {
        title: "Re-seat the front camera USB cable at the camera end",
        body: "Locate the USB cable at the back of the front camera. Unplug it and push it back in firmly.",
        physical: true,
      },
      {
        title: "Re-seat the USB cable at the host end",
        body: "Follow the cable from the camera to its USB port on the REECU or USB hub. Unplug and re-seat the connector.",
        physical: true,
      },
      {
        title: "Inspect the cable for damage",
        body: "Look for visible kinks, cuts, or bent connector pins along the full cable run.",
        physical: true,
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "USB enumeration",
        body:
          "On the host, list USB devices:\n" +
          "  lsusb\n" +
          "  lsusb -v | grep -A5 'Front\\|Camera'\n" +
          "Expected: camera appears with its vendor/product ID. If absent, the USB device is not powered or the cable is faulty.",
      },
      {
        label: "udev / device node",
        body:
          "Check if a video device node was created:\n" +
          "  ls -l /dev/video*\n" +
          "  udevadm monitor --environment\n" +
          "No /dev/videoN → kernel did not bind a driver. Check dmesg for USB errors:\n" +
          "  dmesg | tail -40 | grep -i 'usb\\|camera\\|video'",
      },
      {
        label: "USB bus errors",
        body:
          "Check for USB resets or power faults:\n" +
          "  dmesg | grep -E 'reset|over-current|disconnect|error' | tail -20\n" +
          "Repeated resets → suspect a damaged cable or underpowered USB hub.",
      },
    ],
  },

  expected_front_camera_connected: {
    steps: [
      {
        title: "Re-seat the front camera USB cable at the camera end",
        body: "Locate the USB cable at the back of the front camera. Unplug it and push it back in firmly.",
        physical: true,
      },
      {
        title: "Re-seat the USB cable at the host end",
        body: "Follow the cable to its USB port on the REECU or USB hub. Unplug and re-seat.",
        physical: true,
      },
      {
        title: "Inspect the cable for damage",
        body: "Look for visible kinks, cuts, or bent pins along the cable run.",
        physical: true,
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "USB enumeration",
        body:
          "On the host:\n" +
          "  lsusb\n" +
          "Camera should appear in the list. If not, the device is not seen on the USB bus — physical connection issue.",
      },
      {
        label: "dmesg USB errors",
        body:
          "  dmesg | grep -E 'usb|video|camera' | tail -20\n" +
          "Look for 'device descriptor read' errors or repeated resets.",
      },
    ],
  },

  left_camera: {
    steps: [
      {
        title: "Re-seat the left camera USB cable at the camera end",
        body: "Locate the USB cable at the back of the left camera. Unplug it and push it back in firmly.",
        physical: true,
      },
      {
        title: "Re-seat the USB cable at the host end",
        body: "Follow the cable to its USB port on the REECU or USB hub. Unplug and re-seat.",
        physical: true,
      },
      {
        title: "Inspect the cable for damage",
        body: "Look for visible kinks, cuts, or bent connector pins along the full cable run.",
        physical: true,
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "USB enumeration",
        body: "On the host:\n  lsusb\nCamera should appear. Absent → physical connection issue.",
      },
      {
        label: "dmesg USB errors",
        body: "  dmesg | grep -E 'usb|video|camera' | tail -20\nLook for resets or device descriptor errors.",
      },
    ],
  },

  expected_left_camera_connected: {
    steps: [
      {
        title: "Re-seat the left camera USB cable at the camera end",
        body: "Locate the USB cable at the back of the left camera. Unplug it and push it back in firmly.",
        physical: true,
      },
      {
        title: "Re-seat the USB cable at the host end",
        body: "Follow the cable to its USB port on the REECU or USB hub. Unplug and re-seat.",
        physical: true,
      },
      {
        title: "Inspect the cable for damage",
        body: "Look for visible kinks, cuts, or bent pins along the cable run.",
        physical: true,
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "USB enumeration",
        body: "On the host:\n  lsusb\nCamera should appear. Absent → physical connection issue.",
      },
      {
        label: "dmesg USB errors",
        body: "  dmesg | grep -E 'usb|video|camera' | tail -20\nLook for resets or device descriptor errors.",
      },
    ],
  },

  right_camera: {
    steps: [
      {
        title: "Re-seat the right camera USB cable at the camera end",
        body: "Locate the USB cable at the back of the right camera. Unplug it and push it back in firmly.",
        physical: true,
      },
      {
        title: "Re-seat the USB cable at the host end",
        body: "Follow the cable to its USB port on the REECU or USB hub. Unplug and re-seat.",
        physical: true,
      },
      {
        title: "Inspect the cable for damage",
        body: "Look for visible kinks, cuts, or bent connector pins along the full cable run.",
        physical: true,
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "USB enumeration",
        body: "On the host:\n  lsusb\nCamera should appear. Absent → physical connection issue.",
      },
      {
        label: "dmesg USB errors",
        body: "  dmesg | grep -E 'usb|video|camera' | tail -20\nLook for resets or device descriptor errors.",
      },
    ],
  },

  expected_right_camera_connected: {
    steps: [
      {
        title: "Re-seat the right camera USB cable at the camera end",
        body: "Locate the USB cable at the back of the right camera. Unplug it and push it back in firmly.",
        physical: true,
      },
      {
        title: "Re-seat the USB cable at the host end",
        body: "Follow the cable to its USB port on the REECU or USB hub. Unplug and re-seat.",
        physical: true,
      },
      {
        title: "Inspect the cable for damage",
        body: "Look for visible kinks, cuts, or bent pins along the cable run.",
        physical: true,
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "USB enumeration",
        body: "On the host:\n  lsusb\nCamera should appear. Absent → physical connection issue.",
      },
      {
        label: "dmesg USB errors",
        body: "  dmesg | grep -E 'usb|video|camera' | tail -20\nLook for resets or device descriptor errors.",
      },
    ],
  },

  vehicle_integration_config_valid: {
    steps: [
      {
        title: "Re-deploy the vehicle configuration",
        body: "Re-deploy the vehicle configuration from the ree-vehicle-configs repository to this host.",
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "Config file location",
        body:
          "Expected config path on the vehicle host (confirm with ree-vehicle-configs documentation).\n" +
          "Check the file is present and well-formed:\n" +
          "  cat /path/to/vehicle_integration_config.yaml\n" +
          "  python3 -c \"import yaml; yaml.safe_load(open('/path/to/config'))\"",
      },
      {
        label: "Schema validation",
        body:
          "The check validates that all required fields are present and no unexpected keys exist.\n" +
          "Compare the deployed config against the expected schema in ree-vehicle-configs.",
      },
    ],
  },

  vehicle_config: {
    steps: [
      {
        title: "Re-deploy the vehicle configuration",
        body: "Re-deploy the vehicle configuration from ree-vehicle-configs and run the check again.",
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "Config file",
        body:
          "Check the config is present and well-formed:\n" +
          "  cat /path/to/vehicle_config.yaml\n" +
          "  python3 -c \"import yaml; yaml.safe_load(open('/path/to/config'))\"\n" +
          "Expected shape: documented in ree-vehicle-configs.",
      },
    ],
  },

  network_addresses_reachable: {
    steps: [
      {
        title: "Confirm the vehicle is on the expected network",
        body: "Check that the vehicle is connected to the same network segment as the REECU and that the network switch or router for this vehicle's port is operational.",
        physical: true,
      },
      {
        title: "Check Ethernet cables",
        body: "Inspect the Ethernet cable from the REECU to the in-vehicle switch or router. Re-seat any loose connectors.",
        physical: true,
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "Ping expected addresses",
        body:
          "On the REECU host, ping the expected vehicle network addresses.\n" +
          "Addresses are defined in the vehicle configuration (network_addresses field).\n" +
          "  ping -c4 <address>\n" +
          "No response → check routing, VLAN membership, or the target service.",
      },
      {
        label: "Interface state",
        body:
          "Check the network interface is up and has the expected IP:\n" +
          "  ip addr show\n" +
          "  ip route show\n" +
          "If the interface is DOWN, check the physical Ethernet connection.",
      },
      {
        label: "IPDU Peplink connectivity",
        body:
          "The Peplink routers (PEPLINK_1 / PEPLINK_2) in the IPDU harness (VS101400) handle WAN.\n" +
          "Their 4-pin Molex power connectors feed from the IPDU harness.\n" +
          "If LAN addresses within the vehicle fail, suspect a misconfigured LAN port rather than the harness.",
      },
    ],
  },

  network: {
    steps: [
      {
        title: "Confirm the vehicle is on the expected network",
        body: "Check that the vehicle is connected to the same network and that the switch or router for this port is operational.",
        physical: true,
      },
      {
        title: "Check Ethernet cables and re-seat connectors",
        body: "Inspect the Ethernet cable from the REECU to the switch. Re-seat any loose connectors.",
        physical: true,
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "Ping expected addresses",
        body:
          "  ping -c4 <expected_address>\n" +
          "Address list is in the vehicle config (network_addresses field).",
      },
      {
        label: "Interface state",
        body:
          "  ip addr show\n" +
          "  ip link show\n" +
          "Interface DOWN → physical cable issue. No IP → DHCP or static config problem.",
      },
    ],
  },

  display_surface_reachable: {
    steps: [
      {
        title: "Confirm the display server is running on this telestation",
        body: "Check that the telestation is powered on and the display server service is running.",
      },
      {
        title: "Restart the display server service if needed",
        body: "If the display server is stopped or crashed, restart it following the standard service restart procedure.",
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "Display server port",
        body:
          "The check connects to the display server on an expected port.\n" +
          "On the telestation host:\n" +
          "  ss -tlnp | grep <expected_port>\n" +
          "  systemctl status <display_server_service>",
      },
      {
        label: "Network reachability",
        body:
          "From the REECU, confirm the telestation host is reachable:\n" +
          "  ping -c4 <telestation_ip>\n" +
          "  nc -zv <telestation_ip> <port>",
      },
    ],
  },

  display_surface: {
    steps: [
      {
        title: "Confirm the display server is running",
        body: "Check the telestation is powered on and the display server is active.",
      },
      {
        title: "Restart the display server if needed",
        body: "If stopped, restart it using the standard procedure.",
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "Service status",
        body:
          "  systemctl status <display_server_service>\n" +
          "  journalctl -u <display_server_service> -n 50",
      },
    ],
  },

  expected_input_devices_connected: {
    steps: [
      {
        title: "Re-seat the steering wheel connector",
        body: "Check and re-seat the cable connecting the steering wheel to the telestation.",
        physical: true,
      },
      {
        title: "Re-seat the pedal connector",
        body: "Check and re-seat the pedal assembly cable and confirm the pedals are powered.",
        physical: true,
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "Input device enumeration",
        body:
          "On the telestation host:\n" +
          "  ls /dev/input/\n" +
          "  udevadm info /dev/input/eventX\n" +
          "  cat /proc/bus/input/devices\n" +
          "Expected devices should appear by name/vendor.",
      },
      {
        label: "USB or serial bus",
        body:
          "If devices are USB:\n" +
          "  lsusb\n" +
          "  dmesg | grep -E 'usb|input|hid' | tail -20\n" +
          "If serial/CAN: check the corresponding bus interface is up.",
      },
    ],
  },

  input_devices: {
    steps: [
      {
        title: "Re-seat the steering wheel connector",
        body: "Re-seat the steering wheel cable at both ends.",
        physical: true,
      },
      {
        title: "Re-seat the pedal connector and confirm power",
        body: "Re-seat the pedal assembly cable and confirm it is powered on.",
        physical: true,
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "Input device list",
        body:
          "  cat /proc/bus/input/devices\n" +
          "  ls /dev/input/by-id/\n" +
          "Check that expected devices are present by name.",
      },
    ],
  },

  telestation_config_valid: {
    steps: [
      {
        title: "Re-deploy the telestation configuration",
        body: "Re-deploy the telestation configuration from ree-vehicle-configs and run the check again.",
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "Config file",
        body:
          "Check the config is present and well-formed:\n" +
          "  cat /path/to/telestation_config.yaml\n" +
          "  python3 -c \"import yaml; yaml.safe_load(open('/path/to/config'))\"\n" +
          "Expected shape documented in ree-vehicle-configs.",
      },
    ],
  },

  telestation_config: {
    steps: [
      {
        title: "Re-deploy the telestation configuration",
        body: "Re-deploy from ree-vehicle-configs and run the check again.",
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "Config file",
        body:
          "  cat /path/to/telestation_config.yaml\n" +
          "  python3 -c \"import yaml; yaml.safe_load(open('/path/to/config'))\"\n" +
          "Compare against expected schema in ree-vehicle-configs.",
      },
    ],
  },

  reecu_wake_line_active: {
    vehicleOnly: true,
    steps: [
      {
        title: "Verify KL15 (ignition) is on",
        body: "Confirm the vehicle ignition or telestation power switch is in the ON position. The WAKE line is only energised when KL15 is active — a 0 V reading with ignition off is normal.",
      },
      {
        title: "Check the KL15 fuse",
        body: "Locate the KL15 fuse in the power distribution box. Replace it if blown and re-run the check.",
        physical: true,
        connectors: [{ id: "K15_Fuse", label: "KL15 Fuse (PDU)" }],
      },
      {
        title: "Re-seat connector X9 (REECU WAKE)",
        body: "Unplug REECU connector X9 and inspect pin 1 for corrosion, bent pins, or a loose crimp. Re-seat the connector firmly until it clicks.",
        physical: true,
      },
      {
        title: "Re-seat APCB_2_VIH connector (vehicle) or Integration harness connector (telestation)",
        body: "Vehicle: find the APCB_2_VIH 12-pin Molex connector on the Vehicle Integration Harness and re-seat it. Telestation: re-seat the Integration harness connector at the REECU end. The WAKE line (orange wire, pin 4 / VIH WAKE_SPLICE) must make clean contact.",
        physical: true,
      },
      {
        title: "Measure the WAKE line voltage",
        body: "With KL15 ON, probe X9 pin 1 to chassis ground. Expected: 11–13 V. If absent, trace the orange wire back through the harness toward the APCB board / FMC130 and the ignition relay.",
        physical: true,
      },
      {
        title: "Re-run the diagnostic",
        body: "After any repair, re-run the diagnostic and confirm the WAKE line check passes.",
      },
    ],
    debugSuggestions: [
      {
        label: "Signal path",
        diagram: WAKE_PATH_SVG,
        body:
          "WAKE (KL15) signal — vehicle path:\n" +
          "FMC130 on APCB board (W65.Orange) → S12 splice in APCB harness\n" +
          "→ APCB_2_VIH pin 4 (W66.Orange) → VIH WAKE_SPLICE\n" +
          "→ CREECU_1 (X8) pins 11 & 38\n\n" +
          "Telestation path:\n" +
          "Ignition relay → Integration harness → REECU X9 pin 1 (KL15, 12 V)",
      },
      {
        label: "Connector: APCB_2_VIH (vehicle)",
        diagram: APCB_2_VIH_SVG,
        photos: photosForPNs(["469921210"]),
        connectors: [{ id: "APCB_2_VIH", label: "APCB_2_VIH" }],
        body:
          "Molex 469921210 · 12-pin female — on the APCB Harness (VS040804).\n" +
          "Pin 4 (Orange, W66) carries the REECU WAKE signal to the VIH splice.\n" +
          "Re-seat both mating faces; inspect for orange wire corrosion or pushed-back pin.",
      },
      {
        label: "REECU X9 — WAKE pin",
        connectors: [
          { id: "REECU_X9", label: "REECU X9 (vehicle)" },
          { id: "CREECU_X9", label: "CREECU X9 (TS)" },
        ],
        body:
          "Pin 1 on X9 carries the KL15 WAKE signal (12 V when ignition ON).\n\n" +
          "Quick checks:\n" +
          "  multimeter: X9 pin 1 → GND, key ON → expect 11–13 V\n" +
          "  if 0 V with key ON: check ignition relay coil and KL15 fuse\n" +
          "  if 0 V at relay output: check KL30 supply to relay coil",
      },
    ],
  },

  peplink_cellular_connected: {
    steps: [
      {
        title: "Check the cellular antenna connections on the Peplink router",
        body: "Locate the Peplink router in the vehicle. Verify that all cellular antenna cables (SMA connectors) are finger-tight and seated fully. A loose antenna is the most common cause of a red status LED.",
        physical: true,
      },
      {
        title: "Inspect the SIM cards",
        body: "Power down the Peplink router, remove each SIM card, check for damage or debris on the contacts, re-seat them firmly, and power the router back on. Wait 60 seconds for the modem to re-register before running the check again.",
        physical: true,
      },
      {
        title: "Confirm signal coverage at the vehicle location",
        body: "Move the vehicle or adjust its orientation if possible — underground car parks and dense buildings can block all cellular bands. Check whether other vehicles at the same site report the same issue.",
      },
      {
        title: "Reboot the Peplink router",
        body: "Use the Peplink web UI (accessible via the modem_url in the vehicle config) or the physical reset button to perform a soft reboot. Wait 2 minutes for all modems to come back online before running the check again.",
        physical: true,
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "Cellular status endpoint",
        body:
          "Authenticate and query WAN status directly from the vehicle:\n" +
          "  TOKEN=$(curl -sSk -X POST <modem_url>/api/auth.token.grant \\\n" +
          "    -H 'Content-Type: application/json' \\\n" +
          "    -d '{\"clientId\":\"<id>\",\"clientSecret\":\"<secret>\"}' \\\n" +
          "    | jq -r .response.accessToken)\n" +
          "  curl -sSk \"<modem_url>/api/status.wan.connection?accessToken=$TOKEN\" | jq .\n" +
          "Look for statusLed == \"green\" on every cellular interface.",
      },
      {
        label: "Signal strength",
        body:
          "In the WAN connection response, check the 'signal' field on each cellular interface.\n" +
          "A value below -100 dBm indicates poor coverage.",
      },
      {
        label: "Vehicle config path",
        body:
          "Gateway credentials are at:\n" +
          "  /etc/ree/config/ree-vehicle-configs/org/vay/vehicles/<vehicle-id>.yaml\n" +
          "under vehicle.modem.gateway_* keys.",
      },
    ],
  },

  peplink_vpn_tunnels_established: {
    steps: [
      {
        title: "Confirm cellular connectivity first",
        body: "PepVPN tunnels run over the cellular uplinks. If the cellular check is also failing, resolve that first — the VPN tunnels will not come up without a working WAN connection.",
      },
      {
        title: "Reboot the Peplink router",
        body: "Use the Peplink web UI or the physical reset button to perform a soft reboot. Wait 3 minutes for all VPN peers to re-negotiate their tunnels before running the check again.",
        physical: true,
      },
      {
        title: "Check the vehicle network is not isolated",
        body: "Confirm there is no firewall rule or VLAN change blocking UDP 4500 (PepVPN port) from the vehicle's cellular IPs to the Vay hub endpoints. Contact the network team if unsure.",
      },
      {
        title: "Run the check again",
        body: "Return to the diagnostic result and run the check again.",
      },
    ],
    debugSuggestions: [
      {
        label: "PepVPN status endpoint",
        body:
          "Query tunnel state directly from the vehicle:\n" +
          "  TOKEN=$(curl -sSk -X POST <modem_url>/api/auth.token.grant \\\n" +
          "    -H 'Content-Type: application/json' \\\n" +
          "    -d '{\"clientId\":\"<id>\",\"clientSecret\":\"<secret>\"}' \\\n" +
          "    | jq -r .response.accessToken)\n" +
          "  curl -sSk \"<modem_url>/api/status.pepvpn?accessToken=$TOKEN\" | jq .\n" +
          "Expected: 5 peers with status == \"CONNECTED\".",
      },
      {
        label: "Peer list",
        body:
          "In the pepvpn response, response.peer[] lists each tunnel.\n" +
          "Peers with status != \"CONNECTED\" will show a reason code.\n" +
          "Common codes: NO_ROUTE (WAN down), AUTH_FAIL (key mismatch), TIMEOUT (hub unreachable).",
      },
    ],
  },
};

// ---------------------------------------------------------------------------
// Telestation-specific guides — override the vehicle guide for the same item ID.
// Looked up first for hostType === "telestation"; falls back to guides[] if absent.
// ---------------------------------------------------------------------------

export const tsGuides: Record<string, RepairGuide> = {
  main_can_bus_reachable: {
    steps: [
      {
        title: "Verify the telestation is powered on",
        body: "Confirm the main power switch is in the ON position and the REECU status LEDs are lit. APP CAN is only active when the telestation is fully booted.",
      },
      {
        title: "Re-seat the TIH_REECU_F connector at the REECU",
        body: "Locate the Integration Harness connector at the REECU end (TIH_REECU_F). Press the locking tab, pull it off, inspect the pins for corrosion or bending, then push it back in firmly until it clicks.",
        physical: true,
        connectors: [{ id: "TIH_REECU_F", label: "TIH_REECU_F" }],
      },
      {
        title: "Re-seat the TIH_Main connectors at the docking interface",
        body: "Find the TIH_Main_M and TIH_Main_F mating pair on the telestation docking side. Disconnect and re-seat both halves. APP CAN (pins 1 & 2) must make clean contact.",
        physical: true,
        connectors: [
          { id: "TIH_Main_M", label: "TIH_Main_M" },
          { id: "TIH_Main_F", label: "TIH_Main_F" },
        ],
      },
      {
        title: "Inspect the Integration Harness for damage",
        body: "Trace the cable run from the REECU to the docking connector. Look for pinching, cuts, or chafing. Pay attention to the yellow (CAN H) and grey (CAN L) twisted pair.",
        physical: true,
      },
      {
        title: "Re-run the diagnostic",
        body: "After any repair, re-run the diagnostic and confirm the APP CAN check passes.",
      },
    ],
    debugSuggestions: [
      {
        label: "Signal path",
        diagram: TS_APP_CAN_PATH_SVG,
        body:
          "APP CAN — telestation path:\n" +
          "REECU PCB X8 (CREECU_X9) → Integration Harness → TIH_REECU_F\n" +
          "→ TIH_Main_M pin 1 (CAN H, Yellow) & pin 2 (CAN L, Gray)\n" +
          "→ TIH_Main_F (vehicle docking interface)\n\n" +
          "Note: the telestation does NOT use VIH_2_REEBOX_F or the Accessory Harness.\n" +
          "The Integration Harness (TIH) is the sole CAN carrier on the TS side.",
      },
      {
        label: "CAN bus health check",
        connectors: [{ id: "CREECU_X9", label: "CREECU X9 (TS)" }],
        body:
          "On the REECU host:\n" +
          "  ip -details link show canX\n" +
          "  candump canX\n\n" +
          "Expected: frames from APP CAN devices when docked to a vehicle.\n" +
          "Bus-off / heavy TX errors → check 120 Ω termination at each harness end.\n" +
          "Silent bus with no errors → suspect open at TIH_REECU_F pin 1 or 2.",
      },
      {
        label: "TIH connector continuity",
        connectors: [
          { id: "TIH_REECU_F", label: "TIH_REECU_F" },
          { id: "TIH_Main_M", label: "TIH_Main_M" },
        ],
        body:
          "Measure continuity across the Integration Harness:\n" +
          "  TIH_REECU_F pin 1 → TIH_Main_M pin 1  (CAN H)\n" +
          "  TIH_REECU_F pin 2 → TIH_Main_M pin 2  (CAN L)\n\n" +
          "Open circuit = broken wire or pushed-back pin inside the TIH.\n" +
          "Also measure termination: TIH_Main_M pin 1 → pin 2 should read ~60 Ω\n" +
          "(two 120 Ω resistors in parallel when the vehicle is connected).",
      },
    ],
  },
};

// ---------------------------------------------------------------------------
// Signal guides — VE-side CAN buses and discrete signals.
// These are reference guides not tied to a live diagnostic check.
// ---------------------------------------------------------------------------

export const signalGuides: Record<string, RepairGuide> = {

  // ---- CAN Bus Overview (Vehicle) -----------------------------------------
  can_bus_overview: {
    vehicleOnly: true,
    steps: [
      {
        title: "Use the system map to locate the failing signal",
        body: "Find the CAN bus that is failing in the map on the right. Each colored line shows which harness and connector carries that bus.",
      },
      {
        title: "Open the dedicated repair guide for that signal",
        body: "Return to the guide list on the left and open the specific repair guide for the failing signal — it includes step-by-step connector re-seating instructions.",
      },
    ],
    debugSuggestions: [
      {
        label: "CAN bus topology",
        diagram: CAN_BUS_OVERVIEW_SVG,
        body:
          "VE CAN buses — source to destination:\n" +
          "  APP CAN (CAN 0)  → Reebox_Main_F  pins 1/2  (Yellow/Gray)\n" +
          "  XCP CAN (CAN 1)  → Reebox_Main_F  pins 3/4  (Green/Gray)\n" +
          "  SCI CAN (CAN 2)  → Reebox_Main_F  pins 5/6  (Gray/Blue)\n" +
          "  BODY CAN         → CIPG_F          pin 4/3  (Red/Blue)\n" +
          "  CHASSIS CAN      → CIPG_F          pin 5/6  (White/Brown)\n" +
          "  DIAG CAN         → IPF_F           pin 26/27 (Yellow/Green)\n" +
          "  POWERTRAIN CAN   → Center Console  harness (VS050900)\n" +
          "  DEPB CAN         → Reebox_DEPB_M   → EPB_M pins 3/4\n" +
          "All buses route through the Vehicle Integration Harness (VIH · VS050100).",
      },
    ],
  },

  // ---- XCP CAN (Vehicle) --------------------------------------------------
  xcp_can_bus: {
    vehicleOnly: true,
    steps: [
      {
        title: "Confirm REEBox is powered on",
        body: "Check that the REEBox LED indicators are illuminated before proceeding.",
        physical: true,
      },
      {
        title: "Re-seat Reebox_Main connector — XCP CAN pins 3 & 4",
        body: "Disconnect and firmly re-seat the 8-pin Reebox_Main connector at the REEBox. XCP CAN H (Green, W19) rides on pin 3 and XCP CAN L (Gray, W8) on pin 4. Confirm the locking tab clicks.",
        physical: true,
        connectors: [{ id: "Reebox_Main_F", label: "Reebox Main" }],
      },
      {
        title: "Re-seat VIH_2_REEBOX_F on the VIH",
        body: "Re-seat the 16-pin Molex connector. XCP CAN is routed through this junction from the REECU X8 board connector.",
        physical: true,
        connectors: [{ id: "VIH_2_REEBOX_F", label: "VIH→REEBox" }],
      },
      {
        title: "Inspect harness for damage",
        body: "Trace the Accessory harness from the VIH to the REEBox. Look for pinching, abrasion, or bent pins on the Green (W19) and Gray (W8) twisted pair.",
        physical: true,
      },
    ],
    debugSuggestions: [
      {
        label: "Signal path",
        diagram: XCP_CAN_PATH_SVG,
        body:
          "XCP CAN (XCP_CAN_H / XCP_CAN_L)\n" +
          "REECU PCB X8 (CREECU_1) — REECU logical port: CAN 1 — nets XCP_H / XCP_L\n" +
          "→ VIH internal splice\n" +
          "→ VIH_2_REEBOX_F  pin 3 (Green W19, H)  &  pin 4 (Gray W8, L)\n" +
          "→ Accessory harness  Reebox_Main_F  pin 3 / pin 4\n" +
          "→ IPDU harness  Reebox_Main_M  pin 3 / pin 4\n" +
          "Twisted pair — Green (H) + Gray (L).",
      },
      {
        label: "Connector: Reebox_Main_F / M",
        diagram: REEBOX_MAIN_F_XCP_SVG,
        body:
          "8-pin female (Accessory VS101500) mates with Reebox_Main_M (IPDU VS101400).\n" +
          "Pin 3 = XCP_CAN_H (Green W19)  |  Pin 4 = XCP_CAN_L (Gray W8)\n" +
          "Re-seat mating pair; confirm no pin backs out when locking tab released.",
        connectors: [{ id: "Reebox_Main_F", label: "Reebox Main" }],
      },
      {
        label: "CAN bus health check",
        body:
          "ip -details link show canX\n" +
          "candump canX\n" +
          "Expected: XCP frames from actuator / sensor nodes.\n" +
          "Bus-off / heavy TX errors → check 120 Ω termination at each end.\n" +
          "Silent bus → suspect open circuit at Reebox_Main_F pin 3 or 4.",
      },
      {
        label: "Continuity test",
        body:
          "Measure Reebox_Main_F.3 → REECU X8 XCP_H net (across VIH splice).\n" +
          "Measure Reebox_Main_F.4 → REECU X8 XCP_L net.\n" +
          "Open circuit → broken wire or damaged splice inside VIH (VS050100).",
      },
    ],
  },

  // ---- SCI CAN (Vehicle) --------------------------------------------------
  sci_can_bus: {
    vehicleOnly: true,
    steps: [
      {
        title: "Confirm REEBox is powered on",
        body: "Check REEBox LED indicators before proceeding.",
        physical: true,
      },
      {
        title: "Re-seat Reebox_Main connector — SCI CAN pins 5 & 6",
        body: "Disconnect and firmly re-seat the 8-pin Reebox_Main connector. SCI CAN H (Gray, W21) is on pin 5 and SCI CAN L (Blue, W20) on pin 6. Confirm the locking tab clicks.",
        physical: true,
        connectors: [{ id: "Reebox_Main_F", label: "Reebox Main" }],
      },
      {
        title: "Re-seat VIH_2_REEBOX_F on the VIH",
        body: "Re-seat the 16-pin Molex connector that bridges the Vehicle Integration Harness to the REEBox.",
        physical: true,
        connectors: [{ id: "VIH_2_REEBOX_F", label: "VIH→REEBox" }],
      },
      {
        title: "Inspect harness for damage",
        body: "Trace the Accessory harness. Look for damage on the Gray (W21) and Blue (W20) twisted pair.",
        physical: true,
      },
    ],
    debugSuggestions: [
      {
        label: "Signal path",
        diagram: SCI_CAN_PATH_SVG,
        body:
          "SCI CAN (SCI_CAN_H / SCI_CAN_L)\n" +
          "REECU PCB X8 (CREECU_1) nets SCI_H / SCI_L\n" +
          "→ VIH internal splice\n" +
          "→ VIH_2_REEBOX_F  pin 5 (Gray W21, H)  &  pin 6 (Blue W20, L)\n" +
          "→ Accessory harness  Reebox_Main_F  pin 5 / pin 6\n" +
          "→ IPDU harness  Reebox_Main_M  pin 5 / pin 6\n" +
          "Twisted pair — Gray (H) + Blue (L).",
      },
      {
        label: "Connector: Reebox_Main_F / M",
        diagram: REEBOX_MAIN_F_SCI_SVG,
        body:
          "8-pin female (Accessory VS101500) mates with Reebox_Main_M (IPDU VS101400).\n" +
          "Pin 5 = SCI_CAN_H (Gray W21)  |  Pin 6 = SCI_CAN_L (Blue W20)\n" +
          "Re-seat mating pair; confirm no pin backs out.",
        connectors: [{ id: "Reebox_Main_F", label: "Reebox Main" }],
      },
      {
        label: "CAN bus health check",
        body:
          "candump canX\n" +
          "Expected: SCI instrument / sensor frames.\n" +
          "Silent bus → open at Reebox_Main_F pin 5 or 6, or damaged W20/W21 inside Accessory harness.",
      },
      {
        label: "Continuity test",
        body:
          "Measure Reebox_Main_F.5 → REECU X8 SCI_H net.\n" +
          "Measure Reebox_Main_F.6 → REECU X8 SCI_L net.\n" +
          "Open circuit → broken splice or wire inside VIH (VS050100).",
      },
    ],
  },

  // ---- BODY CAN (Vehicle) -------------------------------------------------
  body_can_bus: {
    vehicleOnly: true,
    steps: [
      {
        title: "Re-seat CIPG connector at the KIAFUSEBOX harness",
        body: "Disconnect and re-seat the CIPG_F / CIPG_M 16-pin connector pair. BODY CAN H (Red, W54) is on pin 4 and BODY CAN L (Blue, W51) on pin 3.",
        physical: true,
      },
      {
        title: "Re-seat VIH_2_KIAFUSEBOX connector on the VIH",
        body: "Re-seat the connector that bridges the Vehicle Integration Harness to the KIAFUSEBOX harness.",
        physical: true,
      },
      {
        title: "Inspect harness for damage",
        body: "Trace the KIAFUSEBOX harness (VS051800). Look for damage on the Red (W54) and Blue (W51) twisted pair around CIPG_F.",
        physical: true,
      },
    ],
    debugSuggestions: [
      {
        label: "Signal path",
        diagram: BODY_CAN_PATH_SVG,
        body:
          "BODY CAN (S_BODY_CAN_H / S_BODY_CAN_L)\n" +
          "REECU PCB X8 (CREECU_1) nets CAN_BODY_H / CAN_BODY_L\n" +
          "→ VIH → VIH_2_KIAFUSEBOX\n" +
          "→ KIAFUSEBOX harness VS051800\n" +
          "→ CIPG_F  pin 4 (Red W54, H)  &  pin 3 (Blue W51, L)\n" +
          "→ CIPG_M  pin 4 (Red W53, H)  &  pin 3 (Blue W52, L)\n" +
          "→ KIA fusebox body control modules\n" +
          "Twisted pairs: W54+W51 (CIPG_F), W53+W52 (CIPG_M).",
      },
      {
        label: "Connector: CIPG_F / CIPG_M",
        diagram: CIPG_F_BODY_SVG,
        body:
          "TE 2005076-1 (F) / 2005079-1 (M) — 16-pin.\n" +
          "Pin 4 = BODY_CAN_H (Red)  |  Pin 3 = BODY_CAN_L (Blue)\n" +
          "Check for bent pins and moisture ingress at both mating faces.",
      },
      {
        label: "CAN bus health check",
        body:
          "candump canX\n" +
          "Expected: body module frames (doors, HVAC, lighting).\n" +
          "Bus-off → check 120 Ω termination at each end.\n" +
          "Silent bus → open circuit at CIPG_F pin 4 or 3.",
      },
      {
        label: "Continuity test",
        body:
          "Measure CIPG_F.4 → REECU X8 CAN_BODY_H net.\n" +
          "Measure CIPG_F.3 → REECU X8 CAN_BODY_L net.\n" +
          "Open → damaged wire in KIAFUSEBOX harness or broken VIH splice.",
      },
    ],
  },

  // ---- CHASSIS CAN (Vehicle) ----------------------------------------------
  chassis_can_bus: {
    vehicleOnly: true,
    steps: [
      {
        title: "Re-seat CIPG connector at the KIAFUSEBOX harness",
        body: "Disconnect and re-seat the CIPG_F / CIPG_M 16-pin connector pair. CHASSIS CAN H (White, W55) is on pin 5 and CHASSIS CAN L (Brown, W58) on pin 6.",
        physical: true,
      },
      {
        title: "Re-seat VIH_2_KIAFUSEBOX on the VIH",
        body: "Re-seat the connector that bridges the VIH to the KIAFUSEBOX harness.",
        physical: true,
      },
      {
        title: "Inspect harness for damage",
        body: "Trace the KIAFUSEBOX harness (VS051800). Look for damage on the White (W55) and Brown (W58) twisted pair.",
        physical: true,
      },
    ],
    debugSuggestions: [
      {
        label: "Signal path",
        diagram: CHASSIS_CAN_PATH_SVG,
        body:
          "CHASSIS CAN (S_CHASSIS_CAN_H / S_CHASSIS_CAN_L)\n" +
          "REECU PCB X8 (CREECU_1) nets CAN_CHASSIS_H / CAN_CHASSIS_L\n" +
          "→ VIH → VIH_2_KIAFUSEBOX\n" +
          "→ KIAFUSEBOX harness VS051800\n" +
          "→ CIPG_F  pin 5 (White W55, H)  &  pin 6 (Brown W58, L)\n" +
          "→ CIPG_M  pin 5 (White W56, H)  &  pin 6 (Brown W57, L)\n" +
          "→ KIA chassis control modules (ABS, ESC, MDPS)\n" +
          "Twisted pairs: W55+W58 (CIPG_F), W56+W57 (CIPG_M).",
      },
      {
        label: "Connector: CIPG_F / CIPG_M",
        diagram: CIPG_F_CHASSIS_SVG,
        body:
          "TE 2005076-1 (F) / 2005079-1 (M) — 16-pin.\n" +
          "Pin 5 = CHASSIS_CAN_H (White)  |  Pin 6 = CHASSIS_CAN_L (Brown)\n" +
          "Check for bent pins, corrosion, and moisture ingress.",
      },
      {
        label: "CAN bus health check",
        body:
          "candump canX\n" +
          "Expected: ABS, ESC, steering frames.\n" +
          "Bus-off → check 120 Ω termination.\n" +
          "Silent bus → open circuit at CIPG_F pin 5 or 6.",
      },
      {
        label: "Continuity test",
        body:
          "Measure CIPG_F.5 → REECU X8 CAN_CHASSIS_H net.\n" +
          "Measure CIPG_F.6 → REECU X8 CAN_CHASSIS_L net.\n" +
          "Open → damaged wire inside VS051800 or broken VIH splice.",
      },
    ],
  },

  // ---- POWERTRAIN / SBW CAN (Vehicle) -------------------------------------
  powertrain_can_bus: {
    vehicleOnly: true,
    steps: [
      {
        title: "Re-seat VIH_2_CENTER_CONSOLE connector",
        body: "Disconnect and firmly re-seat the connector between the Vehicle Integration Harness and the Center Console harness. Powertrain / SBW CAN routes exclusively through this connector — it does NOT pass through the Accessory (REEBox) harness.",
        physical: true,
      },
      {
        title: "Re-seat the Center Console harness at both ends",
        body: "Re-seat both ends of the Center Console harness (VS050900). Confirm all tabs click and no pins are backed out.",
        physical: true,
      },
      {
        title: "Inspect harness for damage",
        body: "Trace the Center Console harness from the VIH to the SBW ECU. Look for pinching or cuts in the Powertrain CAN twisted pair.",
        physical: true,
      },
    ],
    debugSuggestions: [
      {
        label: "Signal path",
        diagram: POWERTRAIN_CAN_PATH_SVG,
        body:
          "POWERTRAIN CAN / SBW CAN (S_PT_H / S_PT_L)\n" +
          "REECU PCB X8 (CREECU_0)  nets CAN_SBW_H / CAN_SBW_L\n" +
          "REECU PCB X8 (CREECU_1)  nets CAN_POWERTRAIN_H / CAN_POWERTRAIN_L\n" +
          "→ VIH splice S_CAN_SBW_H / S_CAN_SBW_L (CREECU_0)\n" +
          "→ VIH splice S_CAN_POWERTRAIN_H / L (CREECU_1)\n" +
          "→ VIH_2_CENTER_CONSOLE connector\n" +
          "→ Center Console harness (VS050900)\n" +
          "→ SBW ECU\n" +
          "Note: APP CAN, BODY CAN, and DIAG CAN do NOT route through Center Console.",
      },
      {
        label: "Connector: VIH_2_CENTER_CONSOLE",
        body:
          "Bridge connector between VIH (VS050100) and Center Console harness (VS050900).\n" +
          "Carries: Powertrain CAN H/L, SBW CAN H/L, WAKE splice.\n" +
          "Does NOT carry: APP CAN, BODY CAN, CHASSIS CAN, DIAG CAN.\n" +
          "Check for bent pins and proper lock engagement.",
      },
      {
        label: "CAN bus health check",
        body:
          "candump canX\n" +
          "Expected: SBW ECU heartbeat frames and powertrain status.\n" +
          "Silent bus → open circuit between VIH and Center Console harness.\n" +
          "Check CREECU_0 and CREECU_1 splices on the VIH for continuity.",
      },
      {
        label: "Splice continuity",
        body:
          "Measure from SBW ECU CAN_H pin → REECU X8 CAN_SBW_H net (across S_CAN_SBW_H splice in VIH).\n" +
          "Measure from SBW ECU CAN_L pin → REECU X8 CAN_SBW_L net.\n" +
          "Open → broken splice or damaged Center Console harness wire.",
      },
    ],
  },

  // ---- DIAGNOSTIC CAN (Vehicle) -------------------------------------------
  diag_can_bus: {
    vehicleOnly: true,
    steps: [
      {
        title: "Re-seat IPF connector at the KIAFUSEBOX harness",
        body: "Disconnect and re-seat the IPF_F / IPF_M 40-pin connector pair. DIAG CAN H (Yellow, W63) is on pin 26 and DIAG CAN L (Green, W64) on pin 27.",
        physical: true,
      },
      {
        title: "Re-seat VIH_2_KIAFUSEBOX on the VIH",
        body: "Re-seat the VIH-to-KIAFUSEBOX bridge connector and confirm the lock engages.",
        physical: true,
      },
      {
        title: "Inspect harness for damage",
        body: "Trace the KIAFUSEBOX harness (VS051800) around IPF_F. Look for damage on the Yellow (W63) and Green (W64) twisted pair.",
        physical: true,
      },
    ],
    debugSuggestions: [
      {
        label: "Signal path",
        diagram: DIAG_CAN_PATH_SVG,
        body:
          "DIAGNOSTIC CAN (S_DIAG_CAN_H / S_DIAG_CAN_L)\n" +
          "REECU PCB X8 nets DIAG_CAN_H / DIAG_CAN_L\n" +
          "→ VIH → VIH_2_KIAFUSEBOX\n" +
          "→ KIAFUSEBOX harness VS051800\n" +
          "→ IPF_F  pin 26 (Yellow W63, H)  &  pin 27 (Green W64, L)\n" +
          "→ IPF_M  pin 26 (Yellow W64, H)  &  pin 27 (Green W65, L)\n" +
          "→ OBD-II / diagnostic gateway\n" +
          "Twisted pair: W63+W64 (IPF_F).",
      },
      {
        label: "Connector: IPF_F / IPF_M",
        diagram: IPF_F_SVG,
        body:
          "Youye YY8401064 (F) / YY940107K (M) — 40-pin.\n" +
          "Pin 26 = DIAG_CAN_H (Yellow W63)  |  Pin 27 = DIAG_CAN_L (Green W64)\n" +
          "Check for bent pins; these connectors are large — ensure full seating.",
      },
      {
        label: "CAN bus health check",
        body:
          "candump canX  (or via OBD-II adapter)\n" +
          "Expected: diagnostic gateway frames, UDS responses.\n" +
          "Silent bus → open at IPF_F pin 26 or 27.",
      },
      {
        label: "Continuity test",
        body:
          "Measure IPF_F.26 → REECU X8 DIAG_CAN_H net.\n" +
          "Measure IPF_F.27 → REECU X8 DIAG_CAN_L net.\n" +
          "Open → damaged wire inside VS051800.",
      },
    ],
  },

  // ---- DEPB CAN (Vehicle) -------------------------------------------------
  depb_can_bus: {
    vehicleOnly: true,
    steps: [
      {
        title: "Re-seat Reebox_DEPB connector on the IPDU harness",
        body: "Locate and firmly re-seat the Reebox_DEPB_M connector on the IPDU harness (VS101400). This connector carries the DEPB CAN bus to the electronic parking brake actuator.",
        physical: true,
        connectors: [{ id: "Reebox_Main_M", label: "IPDU harness" }],
      },
      {
        title: "Re-seat the DEPB Extension harness connectors",
        body: "Re-seat both ends of the DEPB Extension harness (VS051000). Check EPB_M and EPB_F connectors — KET MG651747-5 / MG641744-5, 4-pin.",
        physical: true,
      },
      {
        title: "Inspect harness for damage",
        body: "Trace the DEPB Extension harness. The power wires are Red 1.5 mm² (W1–W4). Look for abrasion or cuts near routing bends.",
        physical: true,
      },
    ],
    debugSuggestions: [
      {
        label: "Signal path",
        diagram: DEPB_CAN_PATH_SVG,
        body:
          "DEPB CAN (DEPB0_CAN_H / DEPB0_CAN_L)\n" +
          "REECU PCB X8 nets DEPB_CAN_H / DEPB_CAN_L\n" +
          "→ VIH → IPDU harness VS101400\n" +
          "→ Reebox_DEPB_M connector\n" +
          "→ DEPB Extension harness VS051000\n" +
          "→ EPB_M (KET MG651747-5)  →  EPB actuator\n" +
          "Power: Red 1.5 mm² W1–W4.",
      },
      {
        label: "Connector: EPB_M / EPB_F",
        diagram: EPB_M_SVG,
        body:
          "KET MG651747-5 (M) / MG641744-5 (F) — 4-pin.\n" +
          "Pin 1 & 2 = motor power (Red 1.5 mm²)\n" +
          "Pin 3 & 4 = CAN H/L\n" +
          "Check for bent pins and proper lock engagement on EPB actuator body.",
      },
      {
        label: "CAN bus health check",
        body:
          "candump canX\n" +
          "Expected: DEPB status frames (position, force, fault code).\n" +
          "Silent bus → open circuit between IPDU and EPB actuator.\n" +
          "No actuator response → also check 12 V supply to EPB_M pins 1 & 2.",
      },
      {
        label: "Power check",
        body:
          "Measure 12 V between EPB_M pin 1 (+) and pin 2 (GND).\n" +
          "No voltage → trace back through DEPB Extension harness to IPDU fuse.\n" +
          "Voltage OK but no CAN → open on pin 3 or 4.",
      },
    ],
  },

  // ---- TS E-Stop Circuit --------------------------------------------------
  ts_estop_circuit: {
    steps: [
      {
        title: "Reset the E-Stop button",
        body: "Twist and release the red E-Stop mushroom button on the telestation. Confirm it pops out fully.",
        physical: true,
      },
      {
        title: "Re-seat E-Stop connector",
        body: "Disconnect and firmly re-seat the E-Stop harness connector at the telestation chassis. Confirm the locking tab clicks.",
        physical: true,
      },
      {
        title: "Re-seat E-Stop loopback harness",
        body: "Re-seat both ends of the E-Stop loopback harness (VS030812). This harness carries three safety loops — Green (W1), White (W2), Blue (W3). Any open loop trips the E-Stop.",
        physical: true,
      },
      {
        title: "Inspect loopback harness for damage",
        body: "Trace all three loop wires (Green W1, White W2, Blue W3). A break in any wire opens the E-Stop circuit.",
        physical: true,
      },
    ],
    debugSuggestions: [
      {
        label: "Circuit path",
        diagram: ESTOP_PATH_SVG,
        body:
          "E-Stop Safety Loops (telestation)\n" +
          "E-Stop button (NC contact) → E_Stop_F connector\n" +
          "→ E-Stop loopback harness VS030812\n" +
          "    Loop 1: Green wire W1\n" +
          "    Loop 2: White wire W2\n" +
          "    Loop 3: Blue  wire W3\n" +
          "→ REECU safety relay input\n" +
          "All three loops must be closed for the system to run.\n" +
          "Open loop = E-Stop tripped.",
      },
      {
        label: "Connector: E_Stop_F (TE 1473410-1)",
        diagram: E_STOP_F_SVG,
        body:
          "TE 1473410-1 — 16-pin.\n" +
          "Carries all three E-Stop loop wires.\n" +
          "Check for pushed-back pins and moisture ingress.\n" +
          "Resistance across each loop pin pair should be < 1 Ω when button is released.",
      },
      {
        label: "Continuity test (per loop)",
        body:
          "With E-Stop button released:\n" +
          "Loop 1: measure resistance across Green W1 pins → < 1 Ω expected.\n" +
          "Loop 2: measure across White W2 pins → < 1 Ω expected.\n" +
          "Loop 3: measure across Blue W3 pins → < 1 Ω expected.\n" +
          "Open loop → broken wire or bent connector pin.",
      },
    ],
  },

  // ---- TS Integration Harness signal path ---------------------------------
  ts_integration_harness: {
    steps: [
      {
        title: "Re-seat TIH_REECU_F on the REECU side",
        body: "Disconnect and re-seat the TIH_REECU_F connector at the REECU board. This carries APP CAN, XCP, SCI and other buses from the REECU into the integration harness.",
        physical: true,
      },
      {
        title: "Re-seat TIH_Main_M / TIH_Main_F at the docking end",
        body: "Re-seat the docking-end connector pair (TIH_Main_M and TIH_Main_F). These mate when the telestation docks to the vehicle. Confirm both sides seat fully.",
        physical: true,
      },
      {
        title: "Inspect integration harness for damage",
        body: "Trace the full length of the Telestation Integration Harness (TIH). Look for pinching, cuts, or loose strain reliefs.",
        physical: true,
      },
    ],
    debugSuggestions: [
      {
        label: "Signal path overview",
        diagram: TIH_PATH_SVG,
        body:
          "Telestation Integration Harness (TIH)\n" +
          "REECU PCB X8 (CREECU_X9)\n" +
          "→ TIH_REECU_F connector\n" +
          "→ Integration harness routes: APP CAN H/L (Yellow/Gray twisted)\n" +
          "   also: XCP CAN, SCI CAN, WAKE, K15, USB, GND\n" +
          "→ TIH_Main_M  (vehicle docking interface)\n" +
          "→ TIH_Main_F  (mates with vehicle-side stub)\n" +
          "Termination: TIH_Main_M pin 1 → pin 2 should read ~60 Ω when vehicle connected.",
      },
      {
        label: "APP CAN on TIH",
        diagram: TS_APP_CAN_PATH_SVG,
        body:
          "APP CAN H/L runs on TIH in Yellow/Gray twisted pair.\n" +
          "Measure TIH_Main_M.1 → TIH_Main_M.2 — expect ~120 Ω (TS-side terminator).\n" +
          "With vehicle docked: ~60 Ω (two 120 Ω resistors in parallel).\n" +
          "No vehicle: candump shows own frames → wiring to REECU is good.\n" +
          "No frames at all → check TIH_REECU_F seating.",
      },
      {
        label: "Continuity test",
        body:
          "Measure TIH_REECU_F APP_CAN_H pin → TIH_Main_M pin 1 (H).\n" +
          "Measure TIH_REECU_F APP_CAN_L pin → TIH_Main_M pin 2 (L).\n" +
          "Open circuit → broken wire inside TIH or pushed-back pin.",
      },
    ],
  },

  // ---- TS Power Supply ----------------------------------------------------
  ts_power_supply: {
    steps: [
      {
        title: "Confirm AC input is connected",
        body: "Check that the IEC AC input cable is fully seated in the AC/DC supply and that the mains socket is live.",
        physical: true,
      },
      {
        title: "Check AC/DC supply output connector",
        body: "Re-seat the DC output connector on the AC/DC supply (EU or US variant). Confirm no bent pins.",
        physical: true,
      },
      {
        title: "Check DC distribution to REECU",
        body: "Trace from the AC/DC supply through the TS power harness to the REECU_POWER connector. Confirm secure seating.",
        physical: true,
      },
    ],
    debugSuggestions: [
      {
        label: "Power chain overview",
        diagram: TS_POWER_PATH_SVG,
        body:
          "Mains (AC) → IEC cable → AC/DC supply (EU: ts-acdc-eu / US: ts-acdc-us)\n" +
          "→ DC output connector → TS Power harness\n" +
          "→ REECU_POWER connector → REECU board 12 V rail\n" +
          "Also feeds: display, Peplink router, fans.\n" +
          "Expected: 12 V DC nominal at REECU_POWER.",
      },
      {
        label: "Voltage checks",
        body:
          "Measure at AC/DC output connector: 12 V DC expected.\n" +
          "Measure at REECU_POWER input: 12 V DC expected.\n" +
          "Under-voltage (< 11 V) → overloaded supply or long cable voltage drop.\n" +
          "No voltage → check mains fuse and IEC cable.",
      },
      {
        label: "LED indicators",
        body:
          "Green LED on AC/DC supply = output OK.\n" +
          "Red or off → over-current or thermal shutdown.\n" +
          "Let supply cool for 5 minutes then re-try. If persistent, swap supply.",
      },
    ],
  },

  // ---- TS XCP CAN ---------------------------------------------------------
  ts_xcp_can: {
    steps: [
      {
        title: "Re-seat TIH_REECU_F connector",
        body: "XCP CAN routes from the REECU PCB through TIH_REECU_F into the integration harness. Re-seat this connector firmly.",
        physical: true,
      },
      {
        title: "Re-seat TIH_Main_M / TIH_Main_F docking connectors",
        body: "Re-seat the docking-end connectors that carry XCP CAN across the vehicle interface.",
        physical: true,
      },
      {
        title: "Inspect integration harness for damage",
        body: "Trace the XCP CAN twisted pair through the TIH. Look for pinching or cuts.",
        physical: true,
      },
    ],
    debugSuggestions: [
      {
        label: "Signal path",
        diagram: TS_XCP_CAN_PATH_SVG,
        body:
          "XCP CAN (telestation side)\n" +
          "REECU PCB X8 (CREECU_X9) XCP_H / XCP_L nets\n" +
          "→ TIH_REECU_F connector\n" +
          "→ Telestation Integration Harness (TIH)\n" +
          "→ TIH_Main_M docking connector\n" +
          "→ (docked) → vehicle XCP CAN network\n" +
          "Twisted pair — same color code as VE side: Green (H) + Gray (L).",
      },
      {
        label: "Connector: TIH_Main_M",
        diagram: TIH_MAIN_M_SVG,
        body:
          "XCP CAN routes on TIH_Main_M connector.\n" +
          "Pin 3 = XCP_CAN_H (Green W19)  |  Pin 4 = XCP_CAN_L (Gray W8)\n" +
          "Measure continuity TIH_REECU_F XCP pins → TIH_Main_M pin 3 / pin 4.",
      },
      {
        label: "CAN bus health check",
        body:
          "candump canX  (run on TS REECU)\n" +
          "Expected: XCP frames from vehicle actuator nodes.\n" +
          "Undocked: no frames expected on XCP (no source).\n" +
          "Docked + silent: open circuit at TIH_REECU_F XCP pins.",
      },
    ],
  },

  // ---- TS SCI CAN ---------------------------------------------------------
  ts_sci_can: {
    steps: [
      {
        title: "Re-seat TIH_REECU_F connector",
        body: "SCI CAN routes through TIH_REECU_F into the integration harness. Re-seat this connector firmly.",
        physical: true,
      },
      {
        title: "Re-seat TIH_Main docking connectors",
        body: "Re-seat the docking-end connectors that carry SCI CAN.",
        physical: true,
      },
      {
        title: "Inspect integration harness for damage",
        body: "Trace the SCI CAN twisted pair (Gray H + Blue L) through the TIH.",
        physical: true,
      },
    ],
    debugSuggestions: [
      {
        label: "Signal path",
        diagram: TS_SCI_CAN_PATH_SVG,
        body:
          "SCI CAN (telestation side)\n" +
          "REECU PCB X8 (CREECU_X9) SCI_H / SCI_L nets\n" +
          "→ TIH_REECU_F connector\n" +
          "→ Telestation Integration Harness (TIH)\n" +
          "→ TIH_Main_M docking connector\n" +
          "→ (docked) → vehicle SCI CAN network\n" +
          "Twisted pair — Gray (H) + Blue (L).",
      },
      {
        label: "Connector: TIH_Main_M",
        diagram: TIH_MAIN_M_SVG,
        body:
          "SCI CAN routes on TIH_Main_M connector.\n" +
          "Pin 5 = SCI_CAN_H (Gray W21)  |  Pin 6 = SCI_CAN_L (Blue W20)\n" +
          "Measure continuity TIH_REECU_F SCI pins → TIH_Main_M pin 5 / pin 6.",
      },
      {
        label: "CAN bus health check",
        body:
          "candump canX  (run on TS REECU)\n" +
          "Expected: SCI instrument frames from vehicle when docked.\n" +
          "Undocked: no frames expected on SCI.\n" +
          "Docked + silent → open circuit at TIH_REECU_F SCI pins.",
      },
    ],
  },
};

// ---------------------------------------------------------------------------
// Offline / unreachable guides — keyed by offline_reason value.
// Looked up in UnreachableState via offlineGuides[reason] ?? offlineGuides.__default.
// ---------------------------------------------------------------------------

export const offlineGuides: Record<string, RepairGuide> = {
  network_unreachable: {
    steps: [
      {
        title: "Confirm the vehicle or telestation is powered on",
        body: "Check the PDU status LEDs and main power switch. The REECU only comes online once PDU output rails are live.",
        physical: true,
      },
      {
        title: "Check the Peplink router status",
        body: "Look at the Peplink router LEDs. A solid green WAN LED means the modem has a data connection. An amber or off LED means the cellular uplink is down — check SIM and antenna.",
        physical: true,
      },
      {
        title: "Verify the network cable from REECU to the in-vehicle switch",
        body: "Unplug and re-seat the Ethernet cable between the REECU and the in-vehicle network switch. A link light should appear on both ends within 10 seconds.",
        physical: true,
      },
      {
        title: "Ping the host from the diagnostic laptop",
        body: "Open a terminal and run: ping <host-ip>. If there is no reply, the route to the host is broken. Try pinging the Peplink router IP first to isolate whether the issue is cellular or LAN.",
      },
      {
        title: "Re-run the diagnostic",
        body: "Once the host responds to ping, re-run the diagnostic to confirm connectivity.",
      },
    ],
    debugSuggestions: [
      {
        label: "Route check",
        body:
          "From the diagnostic laptop:\n" +
          "  ping <host-ip>            # basic reachability\n" +
          "  traceroute <host-ip>      # where does routing stop?\n" +
          "  ip route get <host-ip>    # verify the local route table\n\n" +
          "If ping fails at hop 1, the issue is LAN-local (cable / switch).\n" +
          "If ping fails at hop 2+, the issue is cellular / VPN routing.",
      },
      {
        label: "Peplink modem status",
        body:
          "SSH into the Peplink admin interface (default 192.168.50.1) or\n" +
          "use the InControl cloud dashboard to check:\n" +
          "  - WAN uplink status (SIM signal, data plan)\n" +
          "  - LAN client list — the REECU should appear with its IP\n" +
          "  - PepVPN tunnel state (if VPN is used for access)",
      },
    ],
  },

  ssh_auth_failed: {
    steps: [
      {
        title: "Verify the operator SSH key is deployed to the REECU",
        body: "The REECU accepts only pre-authorised operator keys. Ask the fleet ops team to confirm your public key is in /home/ree/.ssh/authorized_keys on the target REECU.",
      },
      {
        title: "Check SSH service is running on the REECU",
        body: "If you have an alternative access path (console cable or jump host), run: systemctl status ssh. If it is not running, start it: systemctl start ssh.",
      },
      {
        title: "Attempt a manual SSH connection",
        body: "From the diagnostic laptop: ssh ree@<host-ip> -v. The verbose output (-v) will show exactly which key was offered and why authentication was rejected.",
      },
      {
        title: "Re-enrol credentials if the key was rotated",
        body: "If your SSH key was recently rotated, re-run the key-provisioning playbook against this host and retry.",
      },
      {
        title: "Re-run the diagnostic",
        body: "After credentials are restored, re-run the diagnostic to confirm SSH access.",
      },
    ],
    debugSuggestions: [
      {
        label: "SSH verbose output",
        body:
          "ssh ree@<host-ip> -vvv 2>&1 | head -60\n\n" +
          "Look for lines like:\n" +
          "  debug1: Offering public key: ...\n" +
          "  debug1: Authentications that can continue: publickey\n" +
          "  Permission denied (publickey)  ← key not accepted\n\n" +
          "If the server sends no 'Authentications' line, sshd may be\n" +
          "misconfigured — check /etc/ssh/sshd_config AllowUsers.",
      },
      {
        label: "Authorized keys check",
        body:
          "Once you have access via console/jump host:\n" +
          "  cat /home/ree/.ssh/authorized_keys\n" +
          "  ls -la /home/ree/.ssh/\n\n" +
          "Permissions must be:\n" +
          "  .ssh/             700 (drwx------)\n" +
          "  authorized_keys   600 (-rw-------)",
      },
    ],
  },

  ssh_timeout: {
    steps: [
      {
        title: "Check if the REECU is responsive",
        body: "Look at the REECU status LEDs. A slow blink usually means the OS is booting; no lights means no power. Wait 60 seconds if the REECU was recently powered on.",
        physical: true,
      },
      {
        title: "Attempt a manual SSH connection with verbose output",
        body: "From the diagnostic laptop: ssh ree@<host-ip> -v -o ConnectTimeout=10. If it hangs at 'connecting', the TCP port is closed — either sshd crashed or a firewall is blocking port 22.",
      },
      {
        title: "Check CPU load on the REECU",
        body: "If you have console access, run: top or uptime. A load average above 10 on a 4-core REECU means the system is overloaded and SSH will time out. Identify the CPU-consuming process.",
      },
      {
        title: "Restart the REECU if it is stuck",
        body: "Graceful: ssh ree@<host-ip> sudo reboot (if SSH partially works).\nHard: cycle PDU power to the REECU rail. Wait 90 seconds for full boot before re-running the diagnostic.",
        physical: true,
      },
      {
        title: "Re-run the diagnostic",
        body: "Once the REECU is responsive, re-run the diagnostic.",
      },
    ],
    debugSuggestions: [
      {
        label: "Port check",
        body:
          "From the diagnostic laptop:\n" +
          "  nc -zv <host-ip> 22          # is port 22 open?\n" +
          "  ssh ree@<host-ip> -o ConnectTimeout=5 -v\n\n" +
          "If nc times out: firewall or sshd not listening.\n" +
          "If nc connects but SSH hangs: sshd is alive but slow (high load?).",
      },
      {
        label: "Process load (via console)",
        body:
          "If you have console access:\n" +
          "  uptime                        # load average\n" +
          "  ps aux --sort=-%cpu | head    # top CPU consumers\n" +
          "  journalctl -u reecu -n 50     # REECU service logs\n\n" +
          "A stuck reecu process can saturate a CPU core.\n" +
          "  systemctl restart reecu       # restart the service",
      },
    ],
  },

  service_unresponsive: {
    steps: [
      {
        title: "SSH to the REECU and check the diagnostic service",
        body: "ssh ree@<host-ip> and run: systemctl status ree-debug. If it shows 'failed' or 'inactive', the service is not running.",
      },
      {
        title: "Review recent service logs",
        body: "Run: journalctl -u ree-debug -n 100 --no-pager. Look for panic, segfault, or 'address already in use' errors that may explain why the service exited.",
      },
      {
        title: "Restart the diagnostic service",
        body: "systemctl restart ree-debug. Wait 10 seconds, then check: systemctl status ree-debug to confirm it is active.",
      },
      {
        title: "Re-run the diagnostic",
        body: "Once the service reports active, re-run the diagnostic.",
      },
    ],
    debugSuggestions: [
      {
        label: "Service status",
        body:
          "ssh ree@<host-ip>\n" +
          "  systemctl status ree-debug\n" +
          "  journalctl -u ree-debug -n 100 --no-pager\n" +
          "  ss -tlnp | grep <port>        # confirm port is listening\n\n" +
          "Common failure modes:\n" +
          "  - port conflict: another process holds the port\n" +
          "  - binary crash: check journalctl for 'core dumped'\n" +
          "  - dependency missing: check /var/log/ree-debug.log",
      },
    ],
  },

  __default: {
    steps: [
      {
        title: "Confirm the host is powered on",
        body: "Check the power LEDs on the REECU and PDU. No lights means no power — check fuses and the main power cable.",
        physical: true,
      },
      {
        title: "Check the network connection",
        body: "Verify the Ethernet cable is seated and the Peplink router is online (green WAN LED). Ping the host IP from the diagnostic laptop to confirm basic network reachability.",
      },
      {
        title: "Verify SSH access",
        body: "Run: ssh ree@<host-ip> -o ConnectTimeout=10. If this fails, the issue is either network (no route) or authentication (wrong key).",
      },
      {
        title: "Restart the host if it is unresponsive",
        body: "If network is up but SSH fails, cycle PDU power to the REECU. Wait 90 seconds for a full boot before retrying.",
        physical: true,
      },
      {
        title: "Re-run the diagnostic",
        body: "Once the host is reachable, re-run the diagnostic.",
      },
    ],
    debugSuggestions: [
      {
        label: "Connectivity quick check",
        body:
          "ping <host-ip>                  # network reachability\n" +
          "ssh ree@<host-ip> -v            # SSH connection attempt\n" +
          "nc -zv <host-ip> 22             # TCP port 22 open?\n\n" +
          "Triage order:\n" +
          "  1. ping fails    → network / routing issue\n" +
          "  2. nc fails      → SSH not listening (sshd down or firewall)\n" +
          "  3. SSH auth fail → key not authorised\n" +
          "  4. SSH timeout   → host overloaded or stuck",
      },
    ],
  },
};
