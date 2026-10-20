"""The request bodies of the firewall policy endpoints."""

from unifi_mcp.models.firewall.action import FirewallPolicyAction
from unifi_mcp.models.firewall.policy import (
    ConnectionState,
    FirewallPolicyDestination,
    FirewallPolicySource,
    IpsecFilter,
)
from unifi_mcp.models.firewall.protocol import IpProtocolScope
from unifi_mcp.models.firewall.schedule import Schedule

__all__ = [
    "ConnectionState",
    "FirewallPolicyAction",
    "FirewallPolicyDestination",
    "FirewallPolicySource",
    "IpProtocolScope",
    "IpsecFilter",
    "Schedule",
]
