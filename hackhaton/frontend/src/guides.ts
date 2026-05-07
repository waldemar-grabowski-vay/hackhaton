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
  VIH_2_REEBOX_F_SVG,
  REEBOX_MAIN_F_SVG,
  WAKE_PATH_SVG,
  APCB_2_VIH_SVG,
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
};

export const guides: Record<string, RepairGuide> = {
  main_can_bus_reachable: {
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
          "REECU PCB X8 (alias CREECU_1) — nets REF_AUX_CAN_H / REF_AUX_CAN_L\n" +
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
