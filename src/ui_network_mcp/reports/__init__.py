"""Pure functions that combine API responses into one summary for a combined tool."""

from ui_network_mcp.reports.client_search import find_clients
from ui_network_mcp.reports.client_summary import build_client_summary
from ui_network_mcp.reports.device_health import build_device_health
from ui_network_mcp.reports.firewall_overview import (
    build_firewall_overview,
    collect_ids,
)
from ui_network_mcp.reports.network_map import build_network_map
from ui_network_mcp.reports.site_health import build_site_health
from ui_network_mcp.reports.switch_ports import build_switch_ports
from ui_network_mcp.reports.topology import build_topology
from ui_network_mcp.reports.unused_objects import build_unused_objects
from ui_network_mcp.reports.voucher_summary import build_voucher_summary
from ui_network_mcp.reports.wifi_overview import build_wifi_overview

__all__ = [
    "build_client_summary",
    "build_device_health",
    "build_firewall_overview",
    "build_network_map",
    "build_site_health",
    "build_switch_ports",
    "build_topology",
    "build_unused_objects",
    "build_voucher_summary",
    "build_wifi_overview",
    "collect_ids",
    "find_clients",
]
