from typing import Any

from unifi_mcp.client import JSON

# Keys in a firewall traffic filter that hold IDs, and the kind of resource and the name key
# that build_firewall_overview adds next to each of them.
FILTER_ID_KEYS = {
    "networkIds": ("networks", "networkNames"),
    "vpnServerIds": ("vpnServers", "vpnServerNames"),
    "applicationIds": ("applications", "applicationNames"),
    "applicationCategoryIds": ("applicationCategories", "applicationCategoryNames"),
    "trafficMatchingListId": ("trafficMatchingLists", "trafficMatchingListName"),
    "siteToSiteVpnTunnelId": ("siteToSiteVpnTunnels", "siteToSiteVpnTunnelName"),
}


def collect_ids(value: Any, key: str) -> set[Any]:
    """Find all values of a key in nested JSON. A list value adds each of its items."""
    found: set[Any] = set()
    if isinstance(value, dict):
        for item_key, item in value.items():
            if item_key == key:
                found.update(item if isinstance(item, list) else [item])
            else:
                found |= collect_ids(item, key)
    elif isinstance(value, list):
        for item in value:
            found |= collect_ids(item, key)
    return found


def add_names(value: Any, names: dict[str, dict[Any, Any]]) -> Any:
    """Copy nested JSON, and add the name of each referenced resource next to its ID."""
    if isinstance(value, list):
        return [add_names(item, names) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: add_names(item, names) for key, item in value.items()}
    for key, (kind, name_key) in FILTER_ID_KEYS.items():
        if key not in value:
            continue
        lookup = names.get(kind, {})
        ids = value[key]
        if isinstance(ids, list):
            result[name_key] = [lookup.get(item_id, item_id) for item_id in ids]
        else:
            result[name_key] = lookup.get(ids, ids)
    return result


def build_firewall_overview(
    site_id: str,
    zones: list[JSON],
    policies: list[JSON],
    names: dict[str, dict[Any, Any]],
) -> JSON:
    """Group the firewall policies by zone pair, and show names next to the IDs."""
    networks = names.get("networks", {})
    zone_names = {zone["id"]: zone.get("name") for zone in zones}

    pairs: dict[tuple[str | None, str | None], list[JSON]] = {}
    for policy in policies:
        source = policy.get("source") or {}
        destination = policy.get("destination") or {}
        summary = {
            "id": policy["id"],
            "name": policy.get("name"),
            "description": policy.get("description"),
            "enabled": policy.get("enabled"),
            "index": policy.get("index"),
            "origin": (policy.get("metadata") or {}).get("origin"),
            "action": policy.get("action"),
            "ipProtocolScope": policy.get("ipProtocolScope"),
            "connectionStateFilter": policy.get("connectionStateFilter"),
            "ipsecFilter": policy.get("ipsecFilter"),
            "schedule": policy.get("schedule"),
            "loggingEnabled": policy.get("loggingEnabled"),
            "sourceFilter": add_names(source.get("trafficFilter"), names),
            "destinationFilter": add_names(destination.get("trafficFilter"), names),
        }
        key = (source.get("zoneId"), destination.get("zoneId"))
        pairs.setdefault(key, []).append(
            {name: item for name, item in summary.items() if item is not None}
        )

    zone_order = {zone["id"]: position for position, zone in enumerate(zones)}

    def pair_order(key: tuple[str | None, str | None]) -> tuple[int, int]:
        last = len(zones)
        return (zone_order.get(key[0], last), zone_order.get(key[1], last))

    def policy_order(policy: JSON) -> tuple[bool, int]:
        index = policy.get("index")
        return (index is None, index or 0)

    return {
        "siteId": site_id,
        "zones": [
            {
                "id": zone["id"],
                "name": zone.get("name"),
                "origin": (zone.get("metadata") or {}).get("origin"),
                "networks": [
                    networks.get(network_id, network_id)
                    for network_id in zone.get("networkIds", [])
                ],
            }
            for zone in zones
        ],
        "policyCount": len(policies),
        "zonePairs": [
            {
                "sourceZone": zone_names.get(source_id, source_id),
                "destinationZone": zone_names.get(destination_id, destination_id),
                "sourceZoneId": source_id,
                "destinationZoneId": destination_id,
                "policies": sorted(
                    pairs[(source_id, destination_id)], key=policy_order
                ),
            }
            for source_id, destination_id in sorted(pairs, key=pair_order)
        ],
    }
