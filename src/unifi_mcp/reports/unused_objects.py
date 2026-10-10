from unifi_mcp.client import JSON
from unifi_mcp.reports.firewall_overview import collect_ids


def named(item: JSON) -> JSON:
    return {"id": item["id"], "name": item.get("name")}


def is_user_defined(item: JSON) -> bool:
    return (item.get("metadata") or {}).get("origin") == "USER_DEFINED"


def build_unused_objects(
    site_id: str,
    resources: dict[str, list[JSON]],
    network_references: list[JSON | Exception],
) -> JSON:
    """Find the configuration objects of a site that nothing uses, and the disabled objects.

    The resources have the keys networks, firewallZones, firewallPolicies, trafficMatchingLists,
    deviceTags, wifiBroadcasts, aclRules, and dnsPolicies. The network_references are in the
    same order as the networks. A failed request is an Exception.
    """
    networks = resources["networks"]
    policies = resources["firewallPolicies"]

    used_lists = collect_ids(policies, "trafficMatchingListId")
    unused_lists = [
        named(item)
        for item in resources["trafficMatchingLists"]
        if item["id"] not in used_lists
    ]

    unreferenced = []
    unknown = []
    for network, references in zip(networks, network_references, strict=True):
        if isinstance(references, Exception):
            unknown.append({**named(network), "error": str(references)})
        elif not network.get("default") and not any(
            resource.get("referenceCount")
            for resource in references.get("referenceResources", [])
        ):
            unreferenced.append({**named(network), "vlanId": network.get("vlanId")})

    custom_zones = [
        zone for zone in resources["firewallZones"] if is_user_defined(zone)
    ]
    empty_zones = [named(zone) for zone in custom_zones if not zone.get("networkIds")]

    empty_tags = [
        named(tag) for tag in resources["deviceTags"] if not tag.get("deviceIds")
    ]

    disabled = {
        kind: [
            {"id": item["id"], "name": item.get("name") or item.get("domain")}
            for item in resources[kind]
            if item.get("enabled") is False
        ]
        for kind in (
            "networks",
            "wifiBroadcasts",
            "firewallPolicies",
            "aclRules",
            "dnsPolicies",
        )
    }

    result = {
        "siteId": site_id,
        "unusedTrafficMatchingLists": unused_lists,
        "networksWithoutReferences": unreferenced,
        "networksWithUnknownReferences": unknown,
        "customZonesWithoutNetworks": empty_zones,
        "deviceTagsWithoutDevices": empty_tags,
        "disabled": {kind: items for kind, items in disabled.items() if items},
    }
    return {key: value for key, value in result.items() if value}
