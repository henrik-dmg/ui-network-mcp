from collections import Counter

from unifi_mcp.client import JSON
from unifi_mcp.reports.device_summary import device_summary


def port_row(port: JSON) -> JSON:
    poe = port.get("poe") or {}
    row = {
        "idx": port.get("idx"),
        "state": port.get("state"),
        "connector": port.get("connector"),
        "speedMbps": port.get("speedMbps"),
        "maxSpeedMbps": port.get("maxSpeedMbps"),
        "poeState": poe.get("state") if poe.get("enabled") else None,
        "poeStandard": poe.get("standard") if poe.get("enabled") else None,
    }
    return {key: value for key, value in row.items() if value is not None}


def is_below_max_speed(port: JSON) -> bool:
    speed, max_speed = port.get("speedMbps"), port.get("maxSpeedMbps")
    return port.get("state") == "UP" and bool(speed and max_speed and speed < max_speed)


def build_switch_ports(site_id: str, devices: list[JSON], clients: list[JSON]) -> JSON:
    """Summarize the ports of each device that has ports, and list the ports that need attention.

    The devices are device details.
    """
    wired = Counter(
        client["uplinkDeviceId"]
        for client in clients
        if client.get("type") == "WIRED" and client.get("uplinkDeviceId")
    )

    rows = []
    issues = []
    for device in devices:
        ports = (device.get("interfaces") or {}).get("ports") or []
        if not ports:
            continue
        states = Counter(port.get("state") for port in ports)
        poe_states = Counter(
            (port.get("poe") or {}).get("state")
            for port in ports
            if (port.get("poe") or {}).get("enabled")
        )
        slow = [port_row(port) for port in ports if is_below_max_speed(port)]
        limited = [
            port.get("idx")
            for port in ports
            if (port.get("poe") or {}).get("state") == "LIMITED"
        ]
        row = device_summary(device, "state")
        row.update(
            {
                "wiredClients": wired.get(device["id"], 0),
                "portsByState": dict(states),
                "poePortsByState": dict(poe_states),
                "portsBelowMaxSpeed": slow,
                "ports": [port_row(port) for port in ports],
            }
        )
        rows.append(row)
        if slow:
            issues.append(
                f"{device.get('name')} has {len(slow)} port(s) that run below their "
                "maximum speed."
            )
        if limited:
            issues.append(
                f"{device.get('name')} has limited PoE power on port(s) "
                f"{', '.join(str(idx) for idx in limited)}."
            )

    return {"siteId": site_id, "issues": issues, "devices": rows}
