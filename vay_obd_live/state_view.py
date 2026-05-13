"""
Configurable State view: 3-level hierarchy.

  Top group (e.g. "VE", "TS")
   └─ Subgroup (e.g. "SSMAN", "Pedals", "Steering")
       └─ Signal pattern (substring-matched against DBC signals)

Persisted to %USERPROFILE%\\.tsdiag\\state_view.json. Format:

    {
      "groups": [
        {"name": "VE", "expanded": true, "subgroups": [
          {"name": "SSMAN", "expanded": true,
           "signals": ["VE_ChA_SSMAN_State", "VE_ChB_SSMAN_State"]},
          ...
        ]},
        {"name": "TS", "expanded": true, "subgroups": [...]}
      ]
    }

Old (2-level) JSONs are migrated automatically: every flat group is moved
under a single "Legacy" top group on first load.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class SubGroup:
    name: str
    signals: list[str] = field(default_factory=list)
    expanded: bool = True


@dataclass
class TopGroup:
    name: str
    subgroups: list[SubGroup] = field(default_factory=list)
    expanded: bool = True


@dataclass
class StateView:
    groups: list[TopGroup] = field(default_factory=list)

    # ----------- (de)serialization -----------
    def to_dict(self) -> dict:
        return {"groups": [asdict(g) for g in self.groups]}

    @classmethod
    def from_dict(cls, data) -> "StateView":
        if not isinstance(data, dict):
            return cls()
        raw_groups = data.get("groups") or []
        if not isinstance(raw_groups, list):
            return cls()

        # Detect legacy 2-level format (group entries with `signals` directly,
        # no `subgroups` key) — wrap under a single "Legacy" top group.
        looks_legacy = bool(raw_groups) and all(
            isinstance(g, dict) and "subgroups" not in g and "signals" in g
            for g in raw_groups
        )
        if looks_legacy:
            log.info("state_view: migrating legacy flat layout to 3-level")
            legacy_subs: list[SubGroup] = []
            for g in raw_groups:
                if not isinstance(g, dict):
                    continue
                legacy_subs.append(SubGroup(
                    name=str(g.get("name") or "Group").strip() or "Group",
                    signals=[str(s).strip() for s in (g.get("signals") or []) if str(s).strip()],
                    expanded=bool(g.get("expanded", True)),
                ))
            return cls(groups=[TopGroup(name="Legacy", subgroups=legacy_subs, expanded=True)])

        # New format
        groups: list[TopGroup] = []
        for g in raw_groups:
            if not isinstance(g, dict):
                continue
            name = str(g.get("name") or "Group").strip() or "Group"
            subs_raw = g.get("subgroups") or []
            subs: list[SubGroup] = []
            if isinstance(subs_raw, list):
                for s in subs_raw:
                    if not isinstance(s, dict):
                        continue
                    sname = str(s.get("name") or "").strip() or "Group"
                    sigs = [str(x).strip() for x in (s.get("signals") or []) if str(x).strip()]
                    subs.append(SubGroup(name=sname, signals=sigs,
                                         expanded=bool(s.get("expanded", True))))
            groups.append(TopGroup(name=name, subgroups=subs, expanded=bool(g.get("expanded", True))))
        return cls(groups=groups)

    # ----------- defaults -----------
    @classmethod
    def default(cls) -> "StateView":
        """Default 3-level layout: VE top group + TS top group."""
        return cls(groups=[
            TopGroup(name="VE", subgroups=[
                SubGroup("SSMAN", [
                    "VE_ChA_SSMAN_State", "VE_ChB_SSMAN_State",
                ]),
                SubGroup("Engagement", [
                    "VE_PRND_STATE", "VE_PRND_OUTPUT",
                    "VE_DISENGAGE_RESPONSE", "VE_TAKEOVER_STATUS",
                    "VIM_State",
                ]),
                SubGroup("Pedals", [
                    "VE_BRAKE_PEDAL_FEEDBACK", "VE_BRAKE_PEDAL_OUTPUT",
                    "VE_THROTTLE_PEDAL_FEEDBACK", "VE_THROTTLE_PEDAL_OUTPUT",
                    "IoHwAb_VE_BrakeInput_Ch1", "IoHwAb_VE_BrakeInput_Ch2",
                    "IoHwAb_VE_ThrottleInput_Ch1", "IoHwAb_VE_ThrottleInput_Ch2",
                    "VE_BRAKE_PRESSURE_BAR", "VE_BRAKE_IS_PRESSED",
                ]),
                SubGroup("Steering", [
                    "VE_STEERING_ANGLE_FEEDBACK", "VE_STEERING_ANGLE_SETPOINT",
                    "VE_STEERING_TORQUE_OUTPUT", "VE_STEERING_WHEEL_VEL_DEGPS",
                    "IoHwAb_VE_SteerInput_Ch1", "IoHwAb_VE_SteerInput_Ch2",
                ]),
                SubGroup("Buttons & E-Stop", [
                    "ESTOP0_ACTIVE", "ESTOP0_FAULT",
                    "ESTOP1_ACTIVE", "ESTOP1_FAULT",
                    "Gway_ParkBrakeSw", "Gway_BrakeFluidSw",
                    "VE_FRONT_WIPER_STATE", "VE_REAR_WIPER_STATE",
                ]),
            ]),
            TopGroup(name="TS", subgroups=[
                SubGroup("SSMAN", [
                    "TS_ChA_SSMAN_State", "TS_ChB_SSMAN_State",
                ]),
                SubGroup("E-Stop & Engagement", [
                    "TS_ESTOP_BUTTON_STATE",
                    "TS_RND_STATE", "TS_PRND_STATE",
                ]),
                SubGroup("Pedals", [
                    "TS_BRAKE_PEDAL_POS", "TS_BRAKE_PEDAL_FORCE", "TS_BRAKE_PEDAL_RATE",
                    "TS_THROTTLE_PEDAL_POS", "TS_THROTTLE_PEDAL_FORCE", "TS_THROTTLE_PEDAL_RATE",
                    "TS_IoHwAb_Brake_Input_ChA", "TS_IoHwAb_Brake_Input_ChB",
                    "TS_IoHwAb_Throttle_Input_ChA", "TS_IoHwAb_Throttle_Input_ChB",
                ]),
                SubGroup("Steering", [
                    "TS_STEERING_ANGLE", "TS_STEERING_ANGLE_RATE", "TS_STEERING_TORQUE",
                ]),
                SubGroup("SAS", [
                    "TS_Com_SteeringWheel_SAS1", "TS_Com_SteeringWheel_SAS2",
                ]),
                SubGroup("Wipers & Indicators", [
                    "TS_TURN_INDICATOR_STATE",
                    "TS_FRONT_WIPER_STATE", "TS_REAR_WIPER_STATE",
                    "TS_WASHER_STATE", "TS_WIPER_INT_VOL_STATE",
                ]),
            ]),
        ])


# -----------------------------------------------------------------------------
# Persistence
# -----------------------------------------------------------------------------
def _config_path() -> Path:
    base = os.environ.get("USERPROFILE") or str(Path.home())
    return Path(base) / ".tsdiag" / "state_view.json"


def load() -> StateView:
    p = _config_path()
    if not p.is_file():
        view = StateView.default()
        save(view)
        log.info("state_view: seeded default at %s", p)
        return view
    try:
        view = StateView.from_dict(json.loads(p.read_text(encoding="utf-8")))
    except Exception:  # noqa: BLE001
        log.exception("state_view: cannot parse %s — using defaults", p)
        return StateView.default()
    if not view.groups:
        return StateView.default()
    return view


def save(view: StateView) -> Path:
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(view.to_dict(), indent=2), encoding="utf-8")
    return p
