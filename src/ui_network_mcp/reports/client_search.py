import re

from ui_network_mcp.client import JSON
from ui_network_mcp.reports.client_summary import client_row


def normalize_mac(value: str) -> str:
    return re.sub(r"[^0-9a-f]", "", value.lower())


def matches(client: JSON, query: str) -> bool:
    """Compare the query with the name, the IP address, and the MAC address of a client.

    The comparison ignores case. For the MAC address, it also ignores the separators.
    """
    text = query.lower()
    for key in ("name", "ipAddress"):
        if text in (client.get(key) or "").lower():
            return True
    # Compare the MAC address only if the query has no characters other than hexadecimal digits
    # and separators. Otherwise a name such as "laptop" matches all MAC addresses with an "a".
    if not re.fullmatch(r"[0-9a-f:.\-]+", text):
        return False
    mac = normalize_mac(query)
    return bool(mac) and mac in normalize_mac(client.get("macAddress") or "")


def find_clients(
    site_id: str, query: str, clients: list[JSON], devices: list[JSON]
) -> JSON:
    """Return the clients that match the query, with the name and model of their uplink device."""
    by_id = {device["id"]: device for device in devices}
    found = [client_row(client, by_id) for client in clients if matches(client, query)]
    return {
        "siteId": site_id,
        "query": query,
        "matchCount": len(found),
        "clients": found,
    }
