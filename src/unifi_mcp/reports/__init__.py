"""Pure functions that combine API responses into one summary for a combined tool."""

from unifi_mcp.reports.device_health import build_device_health
from unifi_mcp.reports.firewall_overview import build_firewall_overview, collect_ids
from unifi_mcp.reports.site_health import build_site_health
from unifi_mcp.reports.topology import build_topology

__all__ = [
    "build_device_health",
    "build_firewall_overview",
    "build_site_health",
    "build_topology",
    "collect_ids",
]
