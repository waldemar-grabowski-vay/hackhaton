"""Peplink router health checks, run over an existing asyncssh connection.

Reads the on-host vehicle YAML, authenticates with each Peplink gateway found
there, then checks cellular LED status and PepVPN tunnel count.

Adapted from check_api.py (originally a standalone CLI using paramiko).
"""

from __future__ import annotations

import asyncio
import json
import shlex
from dataclasses import dataclass

import yaml

from vayobd.logging import get_logger

log = get_logger(__name__)

VEHICLE_CONFIG_DIR = "/etc/ree/config/ree-vehicle-configs/org/vay/vehicles"
EXPECTED_TUNNELS = 5
_CURL_TIMEOUT = 10


@dataclass
class _Gateway:
    name: str
    base_url: str
    client_id: str
    client_secret: str


async def run_checks(conn, vehicle_id: str, timeout: float) -> tuple[bool, bool, str]:
    """Return (cellular_ok, vpn_ok, raw_detail) for all Peplink gateways.

    Never raises — all failures are captured in raw_detail so the caller can
    always emit two ItemResults.
    """
    rc, out, err = await _run(conn, f"cat {shlex.quote(f'{VEHICLE_CONFIG_DIR}/{vehicle_id}.yaml')}", timeout)
    if rc != 0:
        msg = f"cannot read vehicle config: {(err or out).strip()}"
        log.warning("peplink_config_missing", vehicle_id=vehicle_id)
        return False, False, msg

    try:
        cfg = yaml.safe_load(out) or {}
    except yaml.YAMLError as exc:
        return False, False, f"vehicle yaml parse error: {exc}"

    gateways = _gateways_from_config(cfg)
    if not gateways:
        return False, False, "no peplink gateways in vehicle.modem.gateway_*"

    all_lines: list[str] = []
    cellular_ok = True
    vpn_ok = True

    for gw in gateways:
        gw_cell_ok, gw_vpn_ok, gw_lines = await _check_gateway(conn, gw, timeout)
        if not gw_cell_ok:
            cellular_ok = False
        if not gw_vpn_ok:
            vpn_ok = False
        all_lines.extend(gw_lines)

    return cellular_ok, vpn_ok, "\n".join(all_lines)


async def _check_gateway(conn, gw: _Gateway, timeout: float) -> tuple[bool, bool, list[str]]:
    lines: list[str] = [f"=== {gw.name} :: {gw.base_url} ==="]

    auth_body = json.dumps({"clientId": gw.client_id, "clientSecret": gw.client_secret})
    rc, out, _ = await _run(conn, _curl("POST", f"{gw.base_url}/api/auth.token.grant", auth_body), timeout)
    if rc != 0:
        lines.append(f"auth curl failed (rc={rc})")
        return False, False, lines
    try:
        token_resp = json.loads(out)
    except json.JSONDecodeError:
        lines.append(f"auth non-JSON: {out[:200]}")
        return False, False, lines
    if token_resp.get("stat") != "ok":
        lines.append(f"auth failed stat={token_resp.get('stat')}: {json.dumps(token_resp)[:200]}")
        return False, False, lines

    token = token_resp["response"]["accessToken"]
    lines.append("auth ok")

    cellular_ok, wan_lines = await _check_cellular(conn, gw.base_url, token, timeout)
    lines.extend(wan_lines)

    vpn_ok, vpn_lines = await _check_vpn(conn, gw.base_url, token, timeout)
    lines.extend(vpn_lines)

    return cellular_ok, vpn_ok, lines


async def _check_cellular(conn, base_url: str, token: str, timeout: float) -> tuple[bool, list[str]]:
    url = f"{base_url}/api/status.wan.connection?accessToken={token}"
    rc, out, _ = await _run(conn, _curl("GET", url), timeout)
    if rc != 0:
        return False, [f"wan curl failed (rc={rc})"]
    try:
        wan = json.loads(out)
    except json.JSONDecodeError:
        return False, [f"wan non-JSON: {out[:200]}"]
    if wan.get("stat") != "ok":
        return False, [f"wan stat={wan.get('stat')}"]

    resp = wan.get("response", {})
    cellulars = [(k, v) for k, v in resp.items() if isinstance(v, dict) and v.get("type") == "cellular"]
    if not cellulars:
        return False, ["no cellular interfaces found"]

    lines: list[str] = []
    all_green = True
    for _, iface in sorted(cellulars, key=lambda kv: kv[1].get("name", "")):
        led = iface.get("statusLed")
        flag = "ok" if led == "green" else "ERROR"
        if led != "green":
            all_green = False
        lines.append(f"  {flag} {iface.get('name')}: statusLed={led}  message={iface.get('message', '')}")
    return all_green, lines


async def _check_vpn(conn, base_url: str, token: str, timeout: float) -> tuple[bool, list[str]]:
    url = f"{base_url}/api/status.pepvpn?accessToken={token}"
    rc, out, _ = await _run(conn, _curl("GET", url), timeout)
    if rc != 0:
        return False, [f"vpn curl failed (rc={rc})"]
    try:
        pepvpn = json.loads(out)
    except json.JSONDecodeError:
        return False, [f"vpn non-JSON: {out[:200]}"]
    if pepvpn.get("stat") != "ok":
        return False, [f"vpn stat={pepvpn.get('stat')}"]

    peers = pepvpn.get("response", {}).get("peer", []) or []
    established = sum(1 for p in peers if p.get("status") == "CONNECTED")
    flag = "ok" if established == EXPECTED_TUNNELS else "ERROR"
    ok = established == EXPECTED_TUNNELS
    return ok, [f"  {flag} pepvpn tunnels: {established}/{len(peers)} (expected {EXPECTED_TUNNELS})"]


def _gateways_from_config(cfg: dict) -> list[_Gateway]:
    modem = (cfg.get("vehicle") or {}).get("modem") or {}
    result = []
    for key in sorted(modem):
        if not key.startswith("gateway_"):
            continue
        gw = modem[key] or {}
        if all(gw.get(k) for k in ("peplink_client_id", "peplink_client_secret", "modem_url")):
            result.append(
                _Gateway(
                    name=key,
                    base_url=gw["modem_url"].rstrip("/"),
                    client_id=gw["peplink_client_id"],
                    client_secret=gw["peplink_client_secret"],
                )
            )
    return result


def _curl(method: str, url: str, body: str | None = None) -> str:
    parts = [
        "curl", "-sSk", "--max-time", str(_CURL_TIMEOUT),
        "-X", method, "-H", "Content-Type: application/json",
    ]
    if body is not None:
        parts += ["-d", body]
    parts.append(url)
    return " ".join(shlex.quote(p) for p in parts)


async def _run(conn, cmd: str, timeout: float) -> tuple[int, str, str]:
    result = await asyncio.wait_for(conn.run(cmd, check=False), timeout=timeout)
    return result.exit_status, result.stdout or "", result.stderr or ""
