from collections import Counter

from unifi_mcp.client import JSON


def build_topology(site_id: str, devices: list[JSON], clients: list[JSON]) -> JSON:
    """Arrange devices into a tree by their uplink device, and count the clients of each device."""
    client_counts: dict[str, Counter[str]] = {}
    remote_clients: Counter[str] = Counter()
    for client in clients:
        uplink = client.get("uplinkDeviceId")
        if uplink:
            client_counts.setdefault(uplink, Counter())[client["type"]] += 1
        else:
            remote_clients[client["type"]] += 1

    nodes: dict[str, JSON] = {}
    for device in devices:
        nodes[device["id"]] = {
            "id": device["id"],
            "name": device.get("name"),
            "model": device.get("model"),
            "state": device.get("state"),
            "ipAddress": device.get("ipAddress"),
            "macAddress": device.get("macAddress"),
            "firmwareVersion": device.get("firmwareVersion"),
            "clients": dict(client_counts.get(device["id"], {})),
            "downlinks": [],
        }

    roots: list[JSON] = []
    for device in devices:
        node = nodes[device["id"]]
        parent_id = (device.get("uplink") or {}).get("deviceId")
        if parent_id in nodes and parent_id != device["id"]:
            nodes[parent_id]["downlinks"].append(node)
        else:
            roots.append(node)

    return {
        "siteId": site_id,
        "deviceCount": len(devices),
        "clientCount": len(clients),
        "clientsWithoutUplinkDevice": dict(remote_clients),
        "roots": roots,
    }
