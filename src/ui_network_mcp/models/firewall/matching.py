"""The values that a traffic filter matches: ports, IP addresses, networks, and other objects."""

from typing import Annotated, Literal

from pydantic import Field, IPvAnyAddress, IPvAnyNetwork

from ui_network_mcp.models.api_model import ApiModel

Port = Annotated[int, Field(ge=1, le=65535)]
MatchOpposite = Annotated[
    bool, Field(description="Match all values except the given values.")
]
TrafficMatchingListId = Annotated[
    str, Field(description="The ID of a traffic matching list.")
]


class PortNumber(ApiModel):
    type: Literal["PORT_NUMBER"]
    value: Port


class PortRange(ApiModel):
    type: Literal["PORT_NUMBER_RANGE"]
    start: Port
    stop: Port


class PortList(ApiModel):
    """Match the given ports and port ranges."""

    type: Literal["PORTS"]
    items: list[Annotated[PortNumber | PortRange, Field(discriminator="type")]] = Field(
        min_length=1
    )
    match_opposite: MatchOpposite = False


class PortTrafficMatchingList(ApiModel):
    """Match the ports of a traffic matching list."""

    type: Literal["TRAFFIC_MATCHING_LIST"]
    traffic_matching_list_id: TrafficMatchingListId
    match_opposite: MatchOpposite = False


PortFilter = Annotated[PortList | PortTrafficMatchingList, Field(discriminator="type")]


class IpAddress(ApiModel):
    type: Literal["IP_ADDRESS"]
    value: IPvAnyAddress


class IpAddressRange(ApiModel):
    type: Literal["IP_ADDRESS_RANGE"]
    start: IPvAnyAddress
    stop: IPvAnyAddress


class Subnet(ApiModel):
    type: Literal["SUBNET"]
    value: IPvAnyNetwork = Field(description="The subnet in CIDR notation.")


class IpAddressList(ApiModel):
    """Match the given IP addresses, IP address ranges, and subnets."""

    type: Literal["IP_ADDRESSES"]
    items: list[
        Annotated[IpAddress | IpAddressRange | Subnet, Field(discriminator="type")]
    ] = Field(min_length=1)
    match_opposite: MatchOpposite = False


class IpAddressTrafficMatchingList(ApiModel):
    """Match the IP addresses of a traffic matching list."""

    type: Literal["TRAFFIC_MATCHING_LIST"]
    traffic_matching_list_id: TrafficMatchingListId
    match_opposite: MatchOpposite = False


IpAddressFilter = Annotated[
    IpAddressList | IpAddressTrafficMatchingList, Field(discriminator="type")
]


class NetworkFilter(ApiModel):
    network_ids: list[str] = Field(min_length=1)
    match_opposite: MatchOpposite = False


class VpnServerFilter(ApiModel):
    vpn_server_ids: list[str] = Field(min_length=1)
    match_opposite: MatchOpposite = False


class SiteToSiteVpnTunnelFilter(ApiModel):
    site_to_site_vpn_tunnel_id: str


class RegionFilter(ApiModel):
    regions: list[Annotated[str, Field(pattern=r"^[A-Z]{2}$")]] = Field(
        min_length=1, description="ISO 3166-1 alpha-2 country codes, for example DE."
    )


class Ipv6IidFilter(ApiModel):
    ipv6_iid: str = Field(
        min_length=1,
        description="The IPv6 interface identifier, for example 2001:db8::1/::ffff:ffff:ffff:ffff.",
    )
    match_opposite: MatchOpposite = False


class MacAddressFilter(ApiModel):
    mac_addresses: list[str] = Field(min_length=1)


class DomainFilter(ApiModel):
    type: Literal["DOMAINS"] = "DOMAINS"
    domains: list[str] = Field(min_length=1)


class ApplicationFilter(ApiModel):
    application_ids: list[int] = Field(
        min_length=1,
        max_length=100,
        description="DPI application IDs from list_dpi_applications.",
    )


class ApplicationCategoryFilter(ApiModel):
    application_category_ids: list[int] = Field(
        min_length=1, description="DPI category IDs from list_dpi_categories."
    )
