"""Tools that create, change, delete, and reorder firewall policies.

The server hides these tools unless UNIFI_ALLOW_WRITES is true.
"""

from typing import Annotated, Literal

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field
from pydantic.alias_generators import to_camel

from unifi_mcp.client import JSON
from unifi_mcp.models import request_body
from unifi_mcp.models.firewall import (
    ConnectionState,
    FirewallPolicyAction,
    FirewallPolicyDestination,
    FirewallPolicySource,
    IpProtocolScope,
    IpsecFilter,
    Schedule,
)
from unifi_mcp.models.firewall.protocol import Ipv4AndIpv6Scope
from unifi_mcp.server.parameters import (
    ADDITIVE_WRITE,
    DESTRUCTIVE_WRITE,
    WRITE_TAG,
    SiteId,
)
from unifi_mcp.server.sites import client_of, resolve_site

TAGS = {WRITE_TAG, "firewall"}
# A policy from a GET request has these fields, but the body of a PUT request does not.
RESPONSE_ONLY_FIELDS = {"id", "index", "metadata"}

Name = Annotated[str, Field(min_length=1)]
ConnectionStates = Annotated[
    Annotated[list[ConnectionState], Field(min_length=1)] | None,
    Field(description="Match only these connection states. Omit it to match all."),
]
Ipsec = Annotated[
    IpsecFilter | None,
    Field(description="Match only IPsec traffic, or only other traffic."),
]
PolicySchedule = Annotated[
    Schedule | None,
    Field(description="The time when the policy is active. Without it, always."),
]
ClearableField = Literal[
    "description", "connection_state_filter", "ipsec_filter", "schedule"
]


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=ADDITIVE_WRITE, tags=TAGS)
    async def create_firewall_policy(
        ctx: Context,
        name: Name,
        action: FirewallPolicyAction,
        source: FirewallPolicySource,
        destination: FirewallPolicyDestination,
        ip_protocol_scope: IpProtocolScope | None = None,
        enabled: bool = True,
        logging_enabled: bool = False,
        description: str | None = None,
        connection_state_filter: ConnectionStates = None,
        ipsec_filter: Ipsec = None,
        schedule: PolicySchedule = None,
        site_id: SiteId = None,
    ) -> JSON:
        """Create a firewall policy for the traffic from the source zone to the destination zone.

        The result is the new policy with its ID. Call list_firewall_zones for the zone IDs.
        Call list_networks, list_traffic_matching_lists, list_vpn_servers, or
        list_dpi_applications for the IDs in a traffic filter. The fields have the same names
        as in the result of get_firewall_policy. If you omit ip_protocol_scope, the policy
        matches IPv4 and IPv6 traffic of all protocols. The console puts the new policy before
        the system-defined policies of the zone pair. To change its position, call
        reorder_firewall_policies.
        """
        site = await resolve_site(ctx, site_id)
        body = request_body(
            name=name,
            description=description,
            enabled=enabled,
            action=action,
            source=source,
            destination=destination,
            ip_protocol_scope=ip_protocol_scope
            or Ipv4AndIpv6Scope(ip_version="IPV4_AND_IPV6"),
            connection_state_filter=connection_state_filter,
            ipsec_filter=ipsec_filter,
            schedule=schedule,
            logging_enabled=logging_enabled,
        )
        return await client_of(ctx).post(f"/v1/sites/{site}/firewall/policies", body)

    @mcp.tool(annotations=DESTRUCTIVE_WRITE, tags=TAGS)
    async def update_firewall_policy(
        ctx: Context,
        firewall_policy_id: str,
        name: Name | None = None,
        description: str | None = None,
        enabled: bool | None = None,
        action: FirewallPolicyAction | None = None,
        source: FirewallPolicySource | None = None,
        destination: FirewallPolicyDestination | None = None,
        ip_protocol_scope: IpProtocolScope | None = None,
        connection_state_filter: ConnectionStates = None,
        ipsec_filter: Ipsec = None,
        schedule: PolicySchedule = None,
        logging_enabled: bool | None = None,
        clear: Annotated[
            list[ClearableField] | None,
            Field(description="The optional fields to remove from the policy."),
        ] = None,
        site_id: SiteId = None,
    ) -> JSON:
        """Change a firewall policy. Give only the fields to change. The result is the changed policy.

        A given field replaces the full field of the policy. For example, a new destination
        replaces the zone and the traffic filter of the destination. If you change only
        logging_enabled, the tool sends a PATCH request, which also works for system-defined
        policies. For all other changes, the tool reads the policy and sends the full policy
        with the changes.
        """
        site = await resolve_site(ctx, site_id)
        path = f"/v1/sites/{site}/firewall/policies/{firewall_policy_id}"
        changes = request_body(
            name=name,
            description=description,
            enabled=enabled,
            action=action,
            source=source,
            destination=destination,
            ip_protocol_scope=ip_protocol_scope,
            connection_state_filter=connection_state_filter,
            ipsec_filter=ipsec_filter,
            schedule=schedule,
            logging_enabled=logging_enabled,
        )
        cleared = {to_camel(field) for field in clear or []}
        if not changes and not cleared:
            raise ToolError("Give at least one field to change.")
        if both := cleared & changes.keys():
            raise ToolError(
                f"Do not give a value for a field in clear: {', '.join(sorted(both))}."
            )
        client = client_of(ctx)
        if changes.keys() == {"loggingEnabled"} and not cleared:
            return await client.patch(path, changes)
        current = await client.get(path)
        body = {
            key: value
            for key, value in current.items()
            if key not in RESPONSE_ONLY_FIELDS | cleared
        }
        return await client.put(path, body | changes)

    @mcp.tool(annotations=DESTRUCTIVE_WRITE, tags=TAGS)
    async def delete_firewall_policy(
        ctx: Context, firewall_policy_id: str, site_id: SiteId = None
    ) -> JSON:
        """Delete a firewall policy. You cannot undo this.

        Call get_firewall_policy first to make sure that the ID is the ID of the correct policy.
        """
        site = await resolve_site(ctx, site_id)
        await client_of(ctx).delete(
            f"/v1/sites/{site}/firewall/policies/{firewall_policy_id}"
        )
        return {"deletedFirewallPolicyId": firewall_policy_id}

    @mcp.tool(annotations=DESTRUCTIVE_WRITE, tags=TAGS)
    async def reorder_firewall_policies(
        ctx: Context,
        source_firewall_zone_id: str,
        destination_firewall_zone_id: str,
        before_system_defined: Annotated[
            list[str],
            Field(description="The policies before the system-defined policies."),
        ],
        after_system_defined: Annotated[
            list[str],
            Field(description="The policies after the system-defined policies."),
        ],
        site_id: SiteId = None,
    ) -> JSON:
        """Set the order of the user-defined firewall policies for one pair of zones.

        The console applies the first policy that matches the traffic. Call
        get_firewall_policy_ordering first, and give the policy IDs of its result in the new
        order.
        """
        site = await resolve_site(ctx, site_id)
        return await client_of(ctx).put(
            f"/v1/sites/{site}/firewall/policies/ordering",
            {
                "orderedFirewallPolicyIds": {
                    "beforeSystemDefined": before_system_defined,
                    "afterSystemDefined": after_system_defined,
                }
            },
            {
                "sourceFirewallZoneId": source_firewall_zone_id,
                "destinationFirewallZoneId": destination_firewall_zone_id,
            },
        )
