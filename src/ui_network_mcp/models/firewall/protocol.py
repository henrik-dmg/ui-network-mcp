"""The IP version and the protocol that a firewall policy matches.

The API specification gives the protocol names in lowercase, but the console uses the uppercase
names of the discriminator mapping, for example TCP and ICMPV6.
"""

from typing import Annotated, Literal

from pydantic import Field

from ui_network_mcp.models.api_model import ApiModel
from ui_network_mcp.models.firewall.matching import MatchOpposite

Ipv4ProtocolName = Literal[
    "AH", "AX_25", "DCCP", "DDP", "EGP", "EIGRP", "ENCAP", "ESP", "ETHERIP", "FC",
    "GGP", "GRE", "HIP", "HMP", "IDPR_CMTP", "IDRP", "IGMP", "IGP", "IP", "IPCOMP",
    "IPENCAP", "IPIP", "ISIS", "ISO_TP4", "L2TP", "MANET", "MOBILITY_HEADER",
    "MPLS_IN_IP", "OSPF", "PIM", "PUP", "RDP", "ROHC", "RSPF", "RSVP", "SCTP", "SHIM6",
    "SKIP", "ST", "TCP", "UDP", "UDPLITE", "VMTP", "VRRP", "WESP", "XNS_IDP", "XTP",
]  # fmt: skip
Ipv6ProtocolName = Literal[
    "AH", "DCCP", "EIGRP", "ESP", "GRE", "IPCOMP", "IPV6", "IPV6_FRAG", "IPV6_NONXT",
    "IPV6_OPTS", "IPV6_ROUTE", "ISIS", "L2TP", "MANET", "MOBILITY_HEADER", "MPLS_IN_IP",
    "OSPF", "PIM", "RSVP", "SCTP", "SHIM6", "TCP", "UDP", "VRRP",
]  # fmt: skip
Ipv4AndIpv6ProtocolName = Literal[
    "AH", "DCCP", "EIGRP", "ESP", "GRE", "IPCOMP", "ISIS", "L2TP", "MANET",
    "MOBILITY_HEADER", "MPLS_IN_IP", "OSPF", "PIM", "RSVP", "SCTP", "SHIM6", "TCP",
    "UDP", "VRRP",
]  # fmt: skip
IcmpType = Literal[
    "ADDRESS_MASK_REPLY", "ADDRESS_MASK_REQUEST", "COMMUNICATION_PROHIBITED",
    "DESTINATION_UNREACHABLE", "ECHO_REPLY", "ECHO_REQUEST", "FRAGMENTATION_NEEDED",
    "HOST_PRECEDENCE_VIOLATION", "HOST_PROHIBITED", "HOST_REDIRECT", "HOST_UNKNOWN",
    "HOST_UNREACHABLE", "IP_HEADER_BAD", "NETWORK_PROHIBITED", "NETWORK_REDIRECT",
    "NETWORK_UNKNOWN", "NETWORK_UNREACHABLE", "PARAMETER_PROBLEM", "PORT_UNREACHABLE",
    "PRECEDENCE_CUTOFF", "PROTOCOL_UNREACHABLE", "REDIRECT", "REQUIRED_OPTION_MISSING",
    "ROUTER_ADVERTISEMENT", "ROUTER_SOLICITATION", "SOURCE_QUENCH",
    "SOURCE_ROUTE_FAILED", "TIME_EXCEEDED", "TIMESTAMP_REPLY", "TIMESTAMP_REQUEST",
    "TOS_HOST_REDIRECT", "TOS_HOST_UNREACHABLE", "TOS_NETWORK_REDIRECT",
    "TOS_NETWORK_UNREACHABLE", "TTL_ZERO_DURING_REASSEMBLY", "TTL_ZERO_DURING_TRANSIT",
]  # fmt: skip
Icmpv6Type = Literal[
    "ADDRESS_UNREACHABLE", "BAD_HEADER", "BEYOND_SCOPE", "COMMUNICATION_PROHIBITED",
    "DESTINATION_UNREACHABLE", "ECHO_REPLY", "ECHO_REQUEST", "FAILED_POLICY",
    "NEIGHBOR_ADVERTISEMENT", "NEIGHBOR_SOLICITATION", "NO_ROUTE", "PACKET_TOO_BIG",
    "PARAMETER_PROBLEM", "PORT_UNREACHABLE", "REDIRECT", "REJECT_ROUTE",
    "ROUTER_ADVERTISEMENT", "ROUTER_SOLICITATION", "TIME_EXCEEDED",
    "TTL_ZERO_DURING_REASSEMBLY", "TTL_ZERO_DURING_TRANSIT", "UNKNOWN_HEADER_TYPE",
    "UNKNOWN_OPTION",
]  # fmt: skip

TYPENAME_HELP = "Match only this message type. Omit it to match all types."


class Ipv4Protocol(ApiModel):
    name: Ipv4ProtocolName


class Icmp(ApiModel):
    name: Literal["ICMP"]
    typename_filter: IcmpType | None = Field(None, description=TYPENAME_HELP)


class Ipv6Protocol(ApiModel):
    name: Ipv6ProtocolName


class Icmpv6(ApiModel):
    name: Literal["ICMPV6"]
    typename_filter: Icmpv6Type | None = Field(None, description=TYPENAME_HELP)


class Ipv4AndIpv6Protocol(ApiModel):
    name: Ipv4AndIpv6ProtocolName


class Ipv4NamedProtocolFilter(ApiModel):
    type: Literal["NAMED_PROTOCOL"]
    protocol: Annotated[Ipv4Protocol | Icmp, Field(discriminator="name")]
    match_opposite: MatchOpposite = False


class Ipv6NamedProtocolFilter(ApiModel):
    type: Literal["NAMED_PROTOCOL"]
    protocol: Annotated[Ipv6Protocol | Icmpv6, Field(discriminator="name")]
    match_opposite: MatchOpposite = False


class Ipv4AndIpv6NamedProtocolFilter(ApiModel):
    type: Literal["NAMED_PROTOCOL"]
    protocol: Ipv4AndIpv6Protocol
    match_opposite: MatchOpposite = False


class ProtocolPreset(ApiModel):
    name: Literal["TCP_UDP"] = "TCP_UDP"


class ProtocolPresetFilter(ApiModel):
    """Match TCP and UDP."""

    type: Literal["PRESET"]
    preset: ProtocolPreset = ProtocolPreset()


class ProtocolNumberFilter(ApiModel):
    type: Literal["PROTOCOL_NUMBER"]
    protocol_number: int = Field(ge=0, le=255, description="The IANA protocol number.")
    match_opposite: MatchOpposite = False


class Ipv4Scope(ApiModel):
    ip_version: Literal["IPV4"]
    protocol_filter: (
        Annotated[
            Ipv4NamedProtocolFilter | ProtocolPresetFilter | ProtocolNumberFilter,
            Field(discriminator="type"),
        ]
        | None
    ) = None


class Ipv6Scope(ApiModel):
    ip_version: Literal["IPV6"]
    protocol_filter: (
        Annotated[
            Ipv6NamedProtocolFilter | ProtocolPresetFilter | ProtocolNumberFilter,
            Field(discriminator="type"),
        ]
        | None
    ) = None


class Ipv4AndIpv6Scope(ApiModel):
    ip_version: Literal["IPV4_AND_IPV6"]
    protocol_filter: (
        Annotated[
            Ipv4AndIpv6NamedProtocolFilter
            | ProtocolPresetFilter
            | ProtocolNumberFilter,
            Field(discriminator="type"),
        ]
        | None
    ) = None


IpProtocolScope = Annotated[
    Ipv4Scope | Ipv6Scope | Ipv4AndIpv6Scope, Field(discriminator="ip_version")
]
