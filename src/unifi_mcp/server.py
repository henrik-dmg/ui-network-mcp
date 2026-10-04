from collections import Counter
from collections.abc import AsyncIterator, Callable
from typing import Annotated, Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.lifespan import lifespan
from mcp.types import ToolAnnotations
from pydantic import Field

from unifi_mcp.client import JSON, MAX_PAGE_SIZE, UniFiClient
from unifi_mcp.config import Settings

INSTRUCTIONS = """\
Tools for the UniFi Network API of one UniFi console.
Most tools operate on one site. If you omit site_id, the server uses the configured default site,
or the only site when the console has exactly one. Call list_sites to find site IDs.
Call get_topology first for an overview of how the devices of a site connect.
"""

FILTER_HELP = (
    "Optional filter expression, for example name.like('AP*') or "
    "and(state.eq('ONLINE'), model.eq('U7PG2')). The filterable properties differ per endpoint."
)

READ_ONLY = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True, open_world_hint=True
)

SiteId = Annotated[
    str | None, Field(description="Site ID. Omit it to use the default site.")
]
Filter = Annotated[str | None, Field(description=FILTER_HELP)]
Limit = Annotated[int, Field(ge=1, le=MAX_PAGE_SIZE, description="Page size (1-200).")]
Offset = Annotated[int, Field(ge=0, description="Number of items to skip.")]


def build_server(
    client_factory: Callable[[], UniFiClient], default_site_id: str | None = None
) -> FastMCP:
    @lifespan
    async def unifi_lifespan(_server: FastMCP) -> AsyncIterator[dict[str, Any]]:
        client = client_factory()
        try:
            yield {"client": client, "default_site_id": default_site_id}
        finally:
            await client.aclose()

    mcp = FastMCP("UniFi Network", instructions=INSTRUCTIONS, lifespan=unifi_lifespan)

    def client_of(ctx: Context) -> UniFiClient:
        return ctx.lifespan_context["client"]

    async def resolve_site(ctx: Context, site_id: str | None) -> str:
        if site_id:
            return site_id
        state = ctx.lifespan_context
        if state["default_site_id"]:
            return state["default_site_id"]
        sites = await client_of(ctx).get_all("/v1/sites")
        if len(sites) != 1:
            names = (
                ", ".join(f"{site['name']} ({site['id']})" for site in sites) or "none"
            )
            raise ToolError(
                f"The console has more than one site. Give a site_id. Sites: {names}"
            )
        state["default_site_id"] = sites[0]["id"]
        return sites[0]["id"]

    async def site_page(
        ctx: Context,
        site_id: str | None,
        resource: str,
        offset: int,
        limit: int,
        filter: str | None = None,
    ) -> JSON:
        site = await resolve_site(ctx, site_id)
        return await client_of(ctx).get_page(
            f"/v1/sites/{site}/{resource}", offset=offset, limit=limit, filter=filter
        )

    async def site_item(
        ctx: Context, site_id: str | None, resource: str, item_id: str
    ) -> JSON:
        site = await resolve_site(ctx, site_id)
        return await client_of(ctx).get(f"/v1/sites/{site}/{resource}/{item_id}")

    @mcp.tool(annotations=READ_ONLY, tags={"read"})
    async def get_application_info(ctx: Context) -> JSON:
        """Get the version of the UniFi Network application. Use it to test the connection."""
        return await client_of(ctx).get("/v1/info")

    @mcp.tool(annotations=READ_ONLY, tags={"read"})
    async def list_sites(
        ctx: Context, filter: Filter = None, limit: Limit = 25, offset: Offset = 0
    ) -> JSON:
        """List the sites on the console. Most other tools need a site ID from this list."""
        return await client_of(ctx).get_page(
            "/v1/sites", offset=offset, limit=limit, filter=filter
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "devices"})
    async def list_devices(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the adopted devices (gateways, switches, access points) of a site.

        Filterable properties include name, model, state, macAddress, ipAddress, and firmwareVersion.
        """
        return await site_page(ctx, site_id, "devices", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "devices"})
    async def get_device(ctx: Context, device_id: str, site_id: SiteId = None) -> JSON:
        """Get the details of one adopted device: ports, radios, uplink, and firmware."""
        return await site_item(ctx, site_id, "devices", device_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "devices"})
    async def get_device_statistics(
        ctx: Context, device_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get the latest statistics of one device: uptime, CPU, memory, load, uplink rates, and radios."""
        return await site_item(
            ctx, site_id, "devices", f"{device_id}/statistics/latest"
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "devices"})
    async def list_pending_devices(
        ctx: Context, filter: Filter = None, limit: Limit = 25, offset: Offset = 0
    ) -> JSON:
        """List the devices on the console that wait for adoption."""
        return await client_of(ctx).get_page(
            "/v1/pending-devices", offset=offset, limit=limit, filter=filter
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "clients"})
    async def list_clients(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the connected clients of a site: wired, wireless, VPN, and Teleport.

        Filterable properties include type (WIRED, WIRELESS, VPN, TELEPORT), macAddress, ipAddress,
        connectedAt, and access.type.
        """
        return await site_page(ctx, site_id, "clients", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "clients"})
    async def get_client(ctx: Context, client_id: str, site_id: SiteId = None) -> JSON:
        """Get the details of one connected client."""
        return await site_item(ctx, site_id, "clients", client_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "networks"})
    async def list_networks(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the networks (VLANs) of a site."""
        return await site_page(ctx, site_id, "networks", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "networks"})
    async def get_network(
        ctx: Context, network_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get the full configuration of one network: VLAN, DHCP, IPv4, and IPv6 settings."""
        return await site_item(ctx, site_id, "networks", network_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "wifi"})
    async def list_wifi_broadcasts(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the Wi-Fi networks (SSIDs) of a site."""
        return await site_page(ctx, site_id, "wifi/broadcasts", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "networks"})
    async def list_wans(
        ctx: Context, site_id: SiteId = None, limit: Limit = 25, offset: Offset = 0
    ) -> JSON:
        """List the WAN interfaces of a site."""
        return await site_page(ctx, site_id, "wans", offset, limit)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "firewall"})
    async def list_firewall_zones(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the firewall zones of a site and the networks in each zone.

        Filterable properties include id, name, metadata.origin, and metadata.configurable.
        """
        return await site_page(ctx, site_id, "firewall/zones", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "firewall"})
    async def get_firewall_zone(
        ctx: Context, firewall_zone_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get one firewall zone and the IDs of its networks."""
        return await site_item(ctx, site_id, "firewall/zones", firewall_zone_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "firewall"})
    async def list_firewall_policies(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the firewall policies of a site. Each policy applies to one source zone and one destination zone.

        Filterable properties include id, name, source.zoneId, destination.zoneId, and metadata.origin.
        For a readable overview of all policies, call get_firewall_overview.
        """
        return await site_page(ctx, site_id, "firewall/policies", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "firewall"})
    async def get_firewall_policy(
        ctx: Context, firewall_policy_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get one firewall policy: action, source, destination, protocol, schedule, and logging."""
        return await site_item(ctx, site_id, "firewall/policies", firewall_policy_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "firewall"})
    async def get_firewall_policy_ordering(
        ctx: Context,
        source_firewall_zone_id: str,
        destination_firewall_zone_id: str,
        site_id: SiteId = None,
    ) -> JSON:
        """Get the order of the user-defined firewall policies for one pair of zones.

        The result has the policy IDs before and after the system-defined policies.
        """
        site = await resolve_site(ctx, site_id)
        return await client_of(ctx).get(
            f"/v1/sites/{site}/firewall/policies/ordering",
            {
                "sourceFirewallZoneId": source_firewall_zone_id,
                "destinationFirewallZoneId": destination_firewall_zone_id,
            },
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "acl"})
    async def list_acl_rules(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the ACL rules of a site. The switches apply these rules to traffic in a network.

        Filterable properties include type, id, enabled, name, action, index, networkId, and
        metadata.origin.
        """
        return await site_page(ctx, site_id, "acl-rules", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "acl"})
    async def get_acl_rule(
        ctx: Context, acl_rule_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get one ACL rule: action, source, destination, and the devices that apply it."""
        return await site_item(ctx, site_id, "acl-rules", acl_rule_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "acl"})
    async def get_acl_rule_ordering(ctx: Context, site_id: SiteId = None) -> JSON:
        """Get the order of the user-defined ACL rules of a site."""
        site = await resolve_site(ctx, site_id)
        return await client_of(ctx).get(f"/v1/sites/{site}/acl-rules/ordering")

    @mcp.tool(annotations=READ_ONLY, tags={"read", "dns"})
    async def list_dns_policies(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the DNS policies (local DNS records and forward rules) of a site.

        Filterable properties include type, id, enabled, domain, ipv4Address, ipv6Address, and
        targetDomain.
        """
        return await site_page(ctx, site_id, "dns/policies", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "dns"})
    async def get_dns_policy(
        ctx: Context, dns_policy_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get one DNS policy."""
        return await site_item(ctx, site_id, "dns/policies", dns_policy_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "firewall"})
    async def list_traffic_matching_lists(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the traffic matching lists of a site. These are named lists of ports or IP addresses.

        Firewall policies refer to these lists by ID. Filterable properties are id and name.
        """
        return await site_page(
            ctx, site_id, "traffic-matching-lists", offset, limit, filter
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "firewall"})
    async def get_traffic_matching_list(
        ctx: Context, traffic_matching_list_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get one traffic matching list and its ports or IP addresses."""
        return await site_item(
            ctx, site_id, "traffic-matching-lists", traffic_matching_list_id
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "topology"})
    async def get_topology(ctx: Context, site_id: SiteId = None) -> JSON:
        """Get the device tree of a site, from the gateway down to each switch and access point.

        Each device shows its state, model, IP address, the number of clients that connect to it,
        and the devices that use it as their uplink. VPN and Teleport clients have no uplink device.
        """
        site = await resolve_site(ctx, site_id)
        client = client_of(ctx)
        devices = await client.get_all(f"/v1/sites/{site}/devices")
        details = await client.gather_limited(
            [f"/v1/sites/{site}/devices/{device['id']}" for device in devices]
        )
        clients = await client.get_all(f"/v1/sites/{site}/clients")
        return build_topology(site, details, clients)

    return mcp


def build_topology(site_id: str, devices: list[JSON], clients: list[JSON]) -> JSON:
    """Arrange devices into a tree by their uplink device, and count the clients of each device."""
    client_counts: dict[str, Counter[str]] = {}
    remote_clients: Counter[str] = Counter()
    for client in clients:
        uplink = client.get("uplinkDeviceId")
        if uplink:
            client_counts.setdefault(uplink, Counter())[client["type"]] += 1
        else:
            remote_clients[client["type"]] += 1

    nodes: dict[str, JSON] = {}
    for device in devices:
        nodes[device["id"]] = {
            "id": device["id"],
            "name": device.get("name"),
            "model": device.get("model"),
            "state": device.get("state"),
            "ipAddress": device.get("ipAddress"),
            "macAddress": device.get("macAddress"),
            "firmwareVersion": device.get("firmwareVersion"),
            "clients": dict(client_counts.get(device["id"], {})),
            "downlinks": [],
        }

    roots: list[JSON] = []
    for device in devices:
        node = nodes[device["id"]]
        parent_id = (device.get("uplink") or {}).get("deviceId")
        if parent_id in nodes and parent_id != device["id"]:
            nodes[parent_id]["downlinks"].append(node)
        else:
            roots.append(node)

    return {
        "siteId": site_id,
        "deviceCount": len(devices),
        "clientCount": len(clients),
        "clientsWithoutUplinkDevice": dict(remote_clients),
        "roots": roots,
    }


def create_server() -> FastMCP:
    settings = Settings()
    return build_server(
        lambda: UniFiClient.from_settings(settings), settings.default_site_id
    )
