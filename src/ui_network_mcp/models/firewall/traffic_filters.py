"""The traffic filters of the source and the destination of a firewall policy.

Each filter has one type. Most types also accept a port filter. If the port filter is omitted,
the policy matches all ports.
"""

from typing import Annotated, Literal

from pydantic import Field

from ui_network_mcp.models.api_model import ApiModel
from ui_network_mcp.models.firewall.matching import (
    ApplicationCategoryFilter,
    ApplicationFilter,
    DomainFilter,
    IpAddressFilter,
    Ipv6IidFilter,
    MacAddressFilter,
    NetworkFilter,
    PortFilter,
    RegionFilter,
    SiteToSiteVpnTunnelFilter,
    VpnServerFilter,
)

SourceMacAddress = Annotated[
    str | None, Field(description="Also match one source MAC address.")
]


class PortTrafficFilter(ApiModel):
    type: Literal["PORT"]
    port_filter: PortFilter


class NetworkTrafficFilter(ApiModel):
    type: Literal["NETWORK"]
    network_filter: NetworkFilter
    port_filter: PortFilter | None = None


class IpAddressTrafficFilter(ApiModel):
    type: Literal["IP_ADDRESS"]
    ip_address_filter: IpAddressFilter
    port_filter: PortFilter | None = None


class Ipv6IidTrafficFilter(ApiModel):
    type: Literal["IPV6_IID"]
    ipv6_iid_filter: Ipv6IidFilter
    port_filter: PortFilter | None = None


class RegionTrafficFilter(ApiModel):
    type: Literal["REGION"]
    region_filter: RegionFilter
    port_filter: PortFilter | None = None


class VpnServerTrafficFilter(ApiModel):
    type: Literal["VPN_SERVER"]
    vpn_server_filter: VpnServerFilter
    port_filter: PortFilter | None = None


class SiteToSiteVpnTunnelTrafficFilter(ApiModel):
    type: Literal["SITE_TO_SITE_VPN_TUNNEL"]
    site_to_site_vpn_tunnel_filter: SiteToSiteVpnTunnelFilter
    port_filter: PortFilter | None = None


class SourceNetworkTrafficFilter(NetworkTrafficFilter):
    mac_address_filter: SourceMacAddress = None


class SourceIpAddressTrafficFilter(IpAddressTrafficFilter):
    mac_address_filter: SourceMacAddress = None


class SourceIpv6IidTrafficFilter(Ipv6IidTrafficFilter):
    mac_address_filter: SourceMacAddress = None


class MacAddressTrafficFilter(ApiModel):
    type: Literal["MAC_ADDRESS"]
    mac_address_filter: MacAddressFilter
    port_filter: PortFilter | None = None


class ApplicationTrafficFilter(ApiModel):
    type: Literal["APPLICATION"]
    application_filter: ApplicationFilter
    port_filter: PortFilter | None = None


class ApplicationCategoryTrafficFilter(ApiModel):
    type: Literal["APPLICATION_CATEGORY"]
    application_category_filter: ApplicationCategoryFilter
    port_filter: PortFilter | None = None


class DomainTrafficFilter(ApiModel):
    type: Literal["DOMAIN"]
    domain_filter: DomainFilter
    port_filter: PortFilter | None = None


SourceTrafficFilter = Annotated[
    PortTrafficFilter
    | SourceNetworkTrafficFilter
    | SourceIpAddressTrafficFilter
    | SourceIpv6IidTrafficFilter
    | MacAddressTrafficFilter
    | RegionTrafficFilter
    | VpnServerTrafficFilter
    | SiteToSiteVpnTunnelTrafficFilter,
    Field(discriminator="type"),
]

DestinationTrafficFilter = Annotated[
    PortTrafficFilter
    | NetworkTrafficFilter
    | IpAddressTrafficFilter
    | Ipv6IidTrafficFilter
    | DomainTrafficFilter
    | ApplicationTrafficFilter
    | ApplicationCategoryTrafficFilter
    | RegionTrafficFilter
    | VpnServerTrafficFilter
    | SiteToSiteVpnTunnelTrafficFilter,
    Field(discriminator="type"),
]
