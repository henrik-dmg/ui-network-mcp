from collections import Counter

from ui_network_mcp.client import JSON

NEWEST_CLIENT_COUNT = 10


def client_row(client: JSON, devices: dict[str, JSON]) -> JSON:
    """Return the main fields of a client, and the name and model of its uplink device."""
    uplink = devices.get(client.get("uplinkDeviceId") or "")
    row = {
        "id": client.get("id"),
        "name": client.get("name"),
        "type": client.get("type"),
        "ipAddress": client.get("ipAddress"),
        "macAddress": client.get("macAddress"),
        "connectedAt": client.get("connectedAt"),
        "access": client.get("access"),
        "uplinkDeviceId": client.get("uplinkDeviceId"),
        "uplinkDeviceName": uplink.get("name") if uplink else None,
        "uplinkDeviceModel": uplink.get("model") if uplink else None,
    }
    return {key: value for key, value in row.items() if value is not None}


def build_client_summary(
    site_id: str, clients: list[JSON], devices: list[JSON]
) -> JSON:
    """Count the clients by type, by access type, and by uplink device, and list the newest clients."""
    by_id = {device["id"]: device for device in devices}
    per_device: dict[str, Counter[str]] = {}
    for client in clients:
        uplink = client.get("uplinkDeviceId")
        if uplink:
            per_device.setdefault(uplink, Counter())[client["type"]] += 1

    uplinks: list[JSON] = [
        {
            "deviceId": device_id,
            "name": (by_id.get(device_id) or {}).get("name"),
            "model": (by_id.get(device_id) or {}).get("model"),
            "total": sum(counts.values()),
            "byType": dict(counts),
        }
        for device_id, counts in per_device.items()
    ]
    newest = sorted(
        (client for client in clients if client.get("connectedAt")),
        key=lambda client: client["connectedAt"],
        reverse=True,
    )[:NEWEST_CLIENT_COUNT]

    return {
        "siteId": site_id,
        "total": len(clients),
        "byType": dict(Counter(client["type"] for client in clients)),
        "byAccessType": dict(
            Counter((client.get("access") or {}).get("type") for client in clients)
        ),
        "withoutUplinkDevice": sum(
            1 for client in clients if not client.get("uplinkDeviceId")
        ),
        "byUplinkDevice": sorted(uplinks, key=lambda row: -row["total"]),
        "newest": [client_row(client, by_id) for client in newest],
    }
