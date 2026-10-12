from collections import defaultdict

from unifi_mcp.client import JSON
from unifi_mcp.reports.wifi_overview import wifi_network_id


def subnet(network: JSON) -> str | None:
    ipv4 = network.get("ipv4Configuration") or {}
    if ipv4.get("hostIpAddress") and ipv4.get("prefixLength"):
        return f"{ipv4['hostIpAddress']}/{ipv4['prefixLength']}"
    return None


def build_network_map(
    site_id: str, networks: list[JSON], zones: list[JSON], broadcasts: list[JSON]
) -> JSON:
    """Show each network with its VLAN, subnet, firewall zone, and WiFi broadcasts.

    The networks are network details.
    """
    zone_of = {
        network_id: zone.get("name")
        for zone in zones
        for network_id in zone.get("networkIds", [])
    }
    ssids: dict[str | None, list[str]] = defaultdict(list)
    for broadcast in broadcasts:
        ssids[wifi_network_id(broadcast.get("network"), networks)].append(
            broadcast["name"]
        )

    rows = []
    vlans: dict[int, list[str]] = defaultdict(list)
    for network in networks:
        vlans[network["vlanId"]].append(network["name"])
        row = {
            "id": network["id"],
            "name": network.get("name"),
            "vlanId": network.get("vlanId"),
            "enabled": network.get("enabled"),
            "default": network.get("default"),
            "management": network.get("management"),
            "subnet": subnet(network),
            "additionalSubnets": (network.get("ipv4Configuration") or {}).get(
                "additionalHostIpSubnets"
            ),
            "dhcp": (
                (network.get("ipv4Configuration") or {}).get("dhcpConfiguration") or {}
            ).get("mode"),
            "zone": zone_of.get(network["id"]),
            "wifiBroadcasts": ssids.get(network["id"], []),
        }
        rows.append({key: value for key, value in row.items() if value is not None})

    issues = [
        f"More than one network uses VLAN {vlan_id}: {', '.join(names)}."
        for vlan_id, names in sorted(vlans.items(), key=lambda item: item[0])
        if len(names) > 1
    ]
    return {
        "siteId": site_id,
        "issues": issues,
        "networks": sorted(rows, key=lambda row: row.get("vlanId") or 0),
    }
