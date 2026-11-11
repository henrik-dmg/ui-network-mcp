from collections import Counter
from itertools import combinations

from ui_network_mcp.client import JSON
from ui_network_mcp.reports.device_summary import device_summary

# A radio with a higher share of retried transmissions than this value is an issue.
HIGH_TX_RETRIES_PCT = 15


def wifi_network_id(reference: JSON | None, networks: list[JSON]) -> str | None:
    """Return the ID of the network that a WiFi broadcast uses.

    A NATIVE reference points to the default network.
    """
    if not reference:
        return None
    if reference.get("type") == "NATIVE":
        return next((n["id"] for n in networks if n.get("default")), None)
    return reference.get("networkId")


def broadcast_summary(broadcast: JSON, networks: list[JSON]) -> JSON:
    devices = broadcast.get("broadcastingDeviceFilter")
    names = {network["id"]: network.get("name") for network in networks}
    network_id = wifi_network_id(broadcast.get("network"), networks)
    summary = {
        "id": broadcast["id"],
        "name": broadcast.get("name"),
        "type": broadcast.get("type"),
        "enabled": broadcast.get("enabled"),
        "security": (broadcast.get("securityConfiguration") or {}).get("type"),
        "network": names.get(network_id, network_id),
        "frequenciesGHz": broadcast.get("broadcastingFrequenciesGHz"),
        "broadcastingDevices": devices or "ALL",
    }
    return {key: value for key, value in summary.items() if value is not None}


def build_wifi_overview(
    site_id: str,
    broadcasts: list[JSON],
    networks: list[JSON],
    access_points: list[JSON],
    statistics: list[JSON | Exception],
    clients: list[JSON],
) -> JSON:
    """Combine the WiFi broadcasts, the radios of each access point, and the wireless clients.

    The access_points are device details. The statistics are in the same order as the
    access_points. A failed statistics request is an Exception.
    """
    client_counts = Counter(
        client["uplinkDeviceId"]
        for client in clients
        if client.get("type") == "WIRELESS" and client.get("uplinkDeviceId")
    )

    rows = []
    for device, stats in zip(access_points, statistics, strict=True):
        retries = {}
        if not isinstance(stats, Exception):
            for radio in (stats.get("interfaces") or {}).get("radios") or []:
                retries[radio.get("frequencyGHz")] = radio.get("txRetriesPct")
        radios = [
            {
                key: value
                for key, value in {
                    **radio,
                    "txRetriesPct": retries.get(radio.get("frequencyGHz")),
                }.items()
                if value is not None
            }
            for radio in (device.get("interfaces") or {}).get("radios") or []
        ]
        row = device_summary(device, "state")
        row["wirelessClients"] = client_counts.get(device["id"], 0)
        row["radios"] = radios
        if isinstance(stats, Exception):
            row["statisticsError"] = str(stats)
        rows.append(row)

    issues = []
    online = [row for row in rows if row.get("state") == "ONLINE"]
    for first, second in combinations(online, 2):
        for radio in first["radios"]:
            for other in second["radios"]:
                if radio.get("channel") is not None and (
                    radio.get("frequencyGHz"),
                    radio.get("channel"),
                ) == (other.get("frequencyGHz"), other.get("channel")):
                    issues.append(
                        f"{first['name']} and {second['name']} use channel "
                        f"{radio['channel']} on {radio['frequencyGHz']} GHz."
                    )
    for row in online:
        for radio in row["radios"]:
            if (radio.get("txRetriesPct") or 0) > HIGH_TX_RETRIES_PCT:
                issues.append(
                    f"{row['name']} has {radio['txRetriesPct']}% transmit retries "
                    f"on {radio.get('frequencyGHz')} GHz."
                )
    disabled = [b["name"] for b in broadcasts if b.get("enabled") is False]
    if disabled:
        issues.append(f"These WiFi broadcasts are disabled: {', '.join(disabled)}.")

    return {
        "siteId": site_id,
        "issues": issues,
        "broadcasts": [broadcast_summary(b, networks) for b in broadcasts],
        "accessPoints": sorted(rows, key=lambda row: -row["wirelessClients"]),
        "wirelessClientCount": sum(client_counts.values()),
    }
