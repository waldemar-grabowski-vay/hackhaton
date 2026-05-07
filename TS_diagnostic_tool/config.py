"""
Central configuration for the TS diagnostic tool POC.

Edit the constants below to match your environment. Everything else in the
project reads from here so you only have to change one place.
"""
from __future__ import annotations

import os
from pathlib import Path

# ---- Remote target -------------------------------------------------------
REMOTE_HOST: str = "10.1.200.15"
REMOTE_USER: str = "wilhelm.leonhardt"
REMOTE_PORT: int = 22
# Set to True to forward your local SSH agent to the remote (equivalent to
# `ssh -A`). Only needed if the remote needs to jump further with your keys.
FORWARD_AGENT: bool = True

# Candidate private-key paths the SSH client should try, in order, before
# falling back to the local SSH agent. Useful on Windows where your keys
# may live in WSL rather than %USERPROFILE%\.ssh\.
SSH_KEY_CANDIDATES: tuple[str, ...] = (
    r"{USERPROFILE}\.ssh\id_ed25519",
    r"{USERPROFILE}\.ssh\id_ecdsa",
    r"{USERPROFILE}\.ssh\id_rsa",
    r"{WSL_HOME}\.ssh\id_ed25519",
    r"{WSL_HOME}\.ssh\id_ecdsa",
    r"{WSL_HOME}\.ssh\id_rsa",
)
WSL_DISTRO: str | None = None

# ---- Local repo paths ----------------------------------------------------
REPO_ROOT: Path = Path(os.environ.get("REE_REECU_ROOT", r"C:\__REPOS\ree-reecu_main"))
ERRQ_PATH: Path = REPO_ROOT / "platform" / "tools" / "errq"

# Primary DBC location (auto-loaded on startup if it exists).
PRIMARY_DBC: Path = REPO_ROOT / "dbc" / "application_protocol.dbc"

# Fallback glob patterns if the primary path doesn't resolve. The loader
# picks the most recently modified match.
DBC_GLOB_PATTERNS: tuple[str, ...] = (
    "dbc/application_protocol.dbc",
    "**/application_protocol.dbc",
    "**/ts_app*.dbc",
    "**/TS_APP*.dbc",
)

# ---- Auto git pull -------------------------------------------------------
# Run `git pull --ff-only` on REPO_ROOT at app start to keep the DBC and
# errq CSVs current. Disable by setting to False if the machine is offline.
AUTO_GIT_PULL: bool = True
GIT_PULL_TIMEOUT_S: int = 20

# ---- CAN capture ---------------------------------------------------------
CAN_DETECT_CMD: str = "ip -br link show type can"
CANDUMP_CMD_TEMPLATE: str = "stdbuf -oL -eL candump -tz -L {iface}"

# ---- UI ------------------------------------------------------------------
MAX_LOG_ROWS: int = 5000
MAX_ERROR_ROWS: int = 2000
UI_REFRESH_MS: int = 100

# Signals to surface in the TS System State panel. Keys are signal-name
# substrings; the panel matches case-insensitively. Anything not present
# in the loaded DBC is silently ignored.
#
# Order matters — entries are added to the panel in the order they first
# appear in incoming frames, so list higher-priority signals first.
TS_STATE_SIGNALS: tuple[str, ...] = (
    # SSMAN — top of panel, highlighted on faulty states.
    "TS_ChA_SSMAN_State",
    "TS_ChB_SSMAN_State",
    "VE_ChA_SSMAN_State",
    "VE_ChB_SSMAN_State",
    # Engagement / e-stop / shifter
    "TS_ESTOP_BUTTON_STATE",
    "TS_RND_STATE",
    "TS_PRND_STATE",
    "VE_PRND_STATE",
    # Pedals (TS commanded + IoHwAb readback)
    "TS_BRAKE_PEDAL_POS",
    "TS_BRAKE_PEDAL_FORCE",
    "TS_BRAKE_PEDAL_RATE",
    "TS_THROTTLE_PEDAL_POS",
    "TS_THROTTLE_PEDAL_FORCE",
    "TS_THROTTLE_PEDAL_RATE",
    "TS_IoHwAb_Brake_Input_ChA",
    "TS_IoHwAb_Brake_Input_ChB",
    "TS_IoHwAb_Throttle_Input_ChA",
    "TS_IoHwAb_Throttle_Input_ChB",
    # Steering
    "TS_STEERING_ANGLE",
    "TS_STEERING_ANGLE_RATE",
    "TS_STEERING_TORQUE",
    "TS_Com_SteeringWheel_SAS1",
    "TS_Com_SteeringWheel_SAS2",
    # Steering column / lever
    "TS_TURN_INDICATOR_STATE",
    "TS_FRONT_WIPER_STATE",
    "TS_REAR_WIPER_STATE",
    "TS_WASHER_STATE",
    "TS_WIPER_INT_VOL_STATE",
)

# Signals whose value drives a coloured indicator in the State panel.
# Each entry maps a signal-name pattern -> {value-string -> "orange"|"red"}.
# Cantools returns enum strings (from VAL_ tables) for matching signals,
# which is why we match on string here.
TS_STATE_INDICATORS: dict[str, dict[str, str]] = {
    # VE-side SSMAN: 23-state enum; warn on disengage faults.
    "VE_ChA_SSMAN_State": {
        "DISENGAGED_FAULT": "orange",
        "DISENGAGED_HARD_FAULT": "red",
    },
    "VE_ChB_SSMAN_State": {
        "DISENGAGED_FAULT": "orange",
        "DISENGAGED_HARD_FAULT": "red",
    },
    # TS-side SSMAN: smaller enum; FAULT is the hard fault.
    "TS_ChA_SSMAN_State": {
        "RECOVERABLE_MRM_B1": "orange",
        "FAULT": "red",
    },
    "TS_ChB_SSMAN_State": {
        "RECOVERABLE_MRM_B1": "orange",
        "FAULT": "red",
    },
    # E-stop pressed = red.
    "TS_ESTOP_BUTTON_STATE": {
        "PRESSED": "red",
    },
}

# Heuristic: message names that carry error payloads (the legacy path
# scanned for these). Kept for backward-compat — the new aggregator path
# uses TS_Ch[AB]_ERRQ_Byte01..64 directly.
ERROR_MESSAGE_HINTS: tuple[str, ...] = ("error", "fault", "dtc", "errq")
