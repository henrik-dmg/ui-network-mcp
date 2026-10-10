from collections import Counter

from unifi_mcp.client import JSON
from unifi_mcp.reports.device_summary import device_summary


def build_site_health(
    site_id: str,
    devices: list[JSON],
    clients: list[JSON],
    pending: list[JSON],
    wans: list[JSON],
) -> JSON:
    """Summarize the state of the devices and clients of a site, and list the issues."""
    not_online = [
        device_summary(device, "state", "ipAddress")
        for device in devices
        if device.get("state") != "ONLINE"
    ]
    updatable = [
        device_summary(device, "firmwareVersion")
        for device in devices
        if device.get("firmwareUpdatable")
    ]
    versions: dict[str, Counter[str]] = {}
    for device in devices:
        if device.get("model") and device.get("firmwareVersion"):
            versions.setdefault(device["model"], Counter())[
                device["firmwareVersion"]
            ] += 1
    mismatches = {
        model: dict(counts) for model, counts in versions.items() if len(counts) > 1
    }
    # The list of pending devices is for the full console. A device with no target site
    # can go to any site.
    site_pending = [
        {key: device.get(key) for key in ("macAddress", "model", "ipAddress", "state")}
        for device in pending
        if site_id in device.get("adoptionTargetSiteIds", [site_id])
    ]

    issues = []
    if not_online:
        issues.append(f"{len(not_online)} device(s) are not online.")
    if updatable:
        issues.append(f"{len(updatable)} device(s) have a firmware update.")
    if mismatches:
        issues.append(
            f"{len(mismatches)} model(s) have different firmware versions: "
            + ", ".join(sorted(mismatches))
            + "."
        )
    if site_pending:
        issues.append(f"{len(site_pending)} device(s) wait for adoption.")

    return {
        "siteId": site_id,
        "issues": issues,
        "devices": {
            "total": len(devices),
            "byState": dict(Counter(device.get("state") for device in devices)),
            "notOnline": not_online,
            "firmwareUpdatable": updatable,
            "firmwareVersionMismatches": mismatches,
        },
        "pendingAdoption": site_pending,
        "wans": [wan.get("name") for wan in wans],
        "clients": {
            "total": len(clients),
            "byType": dict(Counter(client.get("type") for client in clients)),
        },
    }
