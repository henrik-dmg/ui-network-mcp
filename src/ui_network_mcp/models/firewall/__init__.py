"""The request bodies of the firewall policy endpoints."""

from ui_network_mcp.models.firewall.action import FirewallPolicyAction
from ui_network_mcp.models.firewall.policy import (
    ConnectionState,
    FirewallPolicyDestination,
    FirewallPolicySource,
    IpsecFilter,
)
from ui_network_mcp.models.firewall.protocol import IpProtocolScope
from ui_network_mcp.models.firewall.schedule import Schedule

__all__ = [
    "ConnectionState",
    "FirewallPolicyAction",
    "FirewallPolicyDestination",
    "FirewallPolicySource",
    "IpProtocolScope",
    "IpsecFilter",
    "Schedule",
]
