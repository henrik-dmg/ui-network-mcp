import asyncio
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
Call get_site_health for a quick status, and get_firewall_overview to explain what traffic
the firewall allows or blocks.
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

    @mcp.tool(annotations=READ_ONLY, tags={"read", "networks"})
    async def get_network_references(
        ctx: Context, network_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get the resources that use one network: clients, devices, Wi-Fi broadcasts, routes, and NAT rules.

        Call this tool before you change or remove a network.
        """
        return await site_item(ctx, site_id, "networks", f"{network_id}/references")

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

    @mcp.tool(annotations=READ_ONLY, tags={"read", "wifi"})
    async def get_wifi_broadcast(
        ctx: Context, wifi_broadcast_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get the full configuration of one Wi-Fi broadcast: network, security, bands, and devices."""
        return await site_item(ctx, site_id, "wifi/broadcasts", wifi_broadcast_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "networks"})
    async def list_wans(
        ctx: Context, site_id: SiteId = None, limit: Limit = 25, offset: Offset = 0
    ) -> JSON:
        """List the WAN interfaces of a site."""
        return await site_page(ctx, site_id, "wans", offset, limit)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "vpn"})
    async def list_vpn_servers(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the VPN servers of a site.

        Filterable properties include type, id, name, enabled, and metadata.origin.
        """
        return await site_page(ctx, site_id, "vpn/servers", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "vpn"})
    async def list_site_to_site_tunnels(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the site-to-site VPN tunnels of a site.

        Filterable properties include type, id, name, metadata.origin, and metadata.source.
        """
        return await site_page(
            ctx, site_id, "vpn/site-to-site-tunnels", offset, limit, filter
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "networks"})
    async def list_radius_profiles(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the RADIUS profiles of a site."""
        return await site_page(ctx, site_id, "radius/profiles", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "devices"})
    async def list_device_tags(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the device tags of a site. Wi-Fi broadcasts can use a tag to select their devices."""
        return await site_page(ctx, site_id, "device-tags", offset, limit, filter)

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

    @mcp.tool(annotations=READ_ONLY, tags={"read", "switching"})
    async def list_lags(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the link aggregation groups (LAGs) of the switches of a site.

        Filterable properties include id, type, switchStackId, mcLagDomainId, and metadata.origin.
        """
        return await site_page(ctx, site_id, "switching/lags", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "switching"})
    async def get_lag(ctx: Context, lag_id: str, site_id: SiteId = None) -> JSON:
        """Get one link aggregation group (LAG). The type is LOCAL, MULTI_CHASSIS, or SWITCH_STACK."""
        return await site_item(ctx, site_id, "switching/lags", lag_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "switching"})
    async def list_mc_lag_domains(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the MC-LAG domains of a site. An MC-LAG domain is a pair of switches that share LAGs."""
        return await site_page(
            ctx, site_id, "switching/mc-lag-domains", offset, limit, filter
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "switching"})
    async def get_mc_lag_domain(
        ctx: Context, mc_lag_domain_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get one MC-LAG domain: its peer switches and its LAGs."""
        return await site_item(
            ctx, site_id, "switching/mc-lag-domains", mc_lag_domain_id
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "switching"})
    async def list_switch_stacks(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the switch stacks of a site."""
        return await site_page(
            ctx, site_id, "switching/switch-stacks", offset, limit, filter
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "switching"})
    async def get_switch_stack(
        ctx: Context, switch_stack_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get one switch stack: its member units and its LAGs."""
        return await site_item(ctx, site_id, "switching/switch-stacks", switch_stack_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "hotspot"})
    async def list_vouchers(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the hotspot vouchers of a site.

        Filterable properties include id, name, code, createdAt, activatedAt, expiresAt, expired,
        and authorizedGuestCount.
        """
        return await site_page(ctx, site_id, "hotspot/vouchers", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "hotspot"})
    async def get_voucher(
        ctx: Context, voucher_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get one hotspot voucher: code, limits, guest count, and expiry."""
        return await site_item(ctx, site_id, "hotspot/vouchers", voucher_id)

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

    @mcp.tool(annotations=READ_ONLY, tags={"read", "firewall"})
    async def get_firewall_overview(ctx: Context, site_id: SiteId = None) -> JSON:
        """Get all firewall zones and policies of a site, grouped by source zone and destination zone.

        In each zone pair, the policies are in the order of their index. The traffic filters show
        the names of the networks, VPN servers, VPN tunnels, traffic matching lists, and DPI
        applications next to their IDs.
        """
        site = await resolve_site(ctx, site_id)
        client = client_of(ctx)
        resources = {
            "zones": "firewall/zones",
            "policies": "firewall/policies",
            "networks": "networks",
            "trafficMatchingLists": "traffic-matching-lists",
            "vpnServers": "vpn/servers",
            "siteToSiteVpnTunnels": "vpn/site-to-site-tunnels",
        }
        lists = await asyncio.gather(
            *(client.get_all(f"/v1/sites/{site}/{path}") for path in resources.values())
        )
        data = dict(zip(resources, lists, strict=True))
        policies = data.pop("policies")
        zones = data.pop("zones")
        if collect_ids(policies, "applicationIds"):
            data["applications"] = await client.get_all("/v1/dpi/applications")
        if collect_ids(policies, "applicationCategoryIds"):
            data["applicationCategories"] = await client.get_all("/v1/dpi/categories")
        names = {
            kind: {item["id"]: item.get("name") for item in items}
            for kind, items in data.items()
        }
        return build_firewall_overview(site, zones, policies, names)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "health"})
    async def get_site_health(ctx: Context, site_id: SiteId = None) -> JSON:
        """Get a health summary of a site. Use it to answer "is everything OK?".

        The summary has a list of issues, the devices by state, the devices that are not online,
        the available firmware updates, models with different firmware versions, the devices that
        wait for adoption, the WAN interfaces, and the clients by type.
        """
        site = await resolve_site(ctx, site_id)
        client = client_of(ctx)
        devices, clients, pending, wans = await asyncio.gather(
            client.get_all(f"/v1/sites/{site}/devices"),
            client.get_all(f"/v1/sites/{site}/clients"),
            client.get_all("/v1/pending-devices"),
            client.get_all(f"/v1/sites/{site}/wans"),
        )
        return build_site_health(site, devices, clients, pending, wans)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "health", "devices"})
    async def get_device_health(ctx: Context, site_id: SiteId = None) -> JSON:
        """Get the latest statistics of all devices of a site, with the device that needs most attention first.

        The devices that are not online come first. The other devices follow, sorted by their
        highest CPU or memory use. Each device shows uptime, CPU, memory, load, and uplink rates.
        """
        site = await resolve_site(ctx, site_id)
        client = client_of(ctx)
        devices = await client.get_all(f"/v1/sites/{site}/devices")
        statistics = await client.gather_limited(
            [
                f"/v1/sites/{site}/devices/{device['id']}/statistics/latest"
                for device in devices
            ],
            return_errors=True,
        )
        return build_device_health(site, devices, statistics)

    return mcp


# Keys in a firewall traffic filter that hold IDs, and the kind of resource and the name key
# that build_firewall_overview adds next to each of them.
FILTER_ID_KEYS = {
    "networkIds": ("networks", "networkNames"),
    "vpnServerIds": ("vpnServers", "vpnServerNames"),
    "applicationIds": ("applications", "applicationNames"),
    "applicationCategoryIds": ("applicationCategories", "applicationCategoryNames"),
    "trafficMatchingListId": ("trafficMatchingLists", "trafficMatchingListName"),
    "siteToSiteVpnTunnelId": ("siteToSiteVpnTunnels", "siteToSiteVpnTunnelName"),
}


def collect_ids(value: Any, key: str) -> set[Any]:
    """Find all values of a key in nested JSON. A list value adds each of its items."""
    found: set[Any] = set()
    if isinstance(value, dict):
        for item_key, item in value.items():
            if item_key == key:
                found.update(item if isinstance(item, list) else [item])
            else:
                found |= collect_ids(item, key)
    elif isinstance(value, list):
        for item in value:
            found |= collect_ids(item, key)
    return found


def add_names(value: Any, names: dict[str, dict[Any, Any]]) -> Any:
    """Copy nested JSON, and add the name of each referenced resource next to its ID."""
    if isinstance(value, list):
        return [add_names(item, names) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: add_names(item, names) for key, item in value.items()}
    for key, (kind, name_key) in FILTER_ID_KEYS.items():
        if key not in value:
            continue
        lookup = names.get(kind, {})
        ids = value[key]
        if isinstance(ids, list):
            result[name_key] = [lookup.get(item_id, item_id) for item_id in ids]
        else:
            result[name_key] = lookup.get(ids, ids)
    return result


def build_firewall_overview(
    site_id: str,
    zones: list[JSON],
    policies: list[JSON],
    names: dict[str, dict[Any, Any]],
) -> JSON:
    """Group the firewall policies by zone pair, and show names next to the IDs."""
    networks = names.get("networks", {})
    zone_names = {zone["id"]: zone.get("name") for zone in zones}

    pairs: dict[tuple[str | None, str | None], list[JSON]] = {}
    for policy in policies:
        source = policy.get("source") or {}
        destination = policy.get("destination") or {}
        summary = {
            "id": policy["id"],
            "name": policy.get("name"),
            "description": policy.get("description"),
            "enabled": policy.get("enabled"),
            "index": policy.get("index"),
            "origin": (policy.get("metadata") or {}).get("origin"),
            "action": policy.get("action"),
            "ipProtocolScope": policy.get("ipProtocolScope"),
            "connectionStateFilter": policy.get("connectionStateFilter"),
            "ipsecFilter": policy.get("ipsecFilter"),
            "schedule": policy.get("schedule"),
            "loggingEnabled": policy.get("loggingEnabled"),
            "sourceFilter": add_names(source.get("trafficFilter"), names),
            "destinationFilter": add_names(destination.get("trafficFilter"), names),
        }
        key = (source.get("zoneId"), destination.get("zoneId"))
        pairs.setdefault(key, []).append(
            {name: item for name, item in summary.items() if item is not None}
        )

    zone_order = {zone["id"]: position for position, zone in enumerate(zones)}

    def pair_order(key: tuple[str | None, str | None]) -> tuple[int, int]:
        last = len(zones)
        return (zone_order.get(key[0], last), zone_order.get(key[1], last))

    def policy_order(policy: JSON) -> tuple[bool, int]:
        index = policy.get("index")
        return (index is None, index or 0)

    return {
        "siteId": site_id,
        "zones": [
            {
                "id": zone["id"],
                "name": zone.get("name"),
                "origin": (zone.get("metadata") or {}).get("origin"),
                "networks": [
                    networks.get(network_id, network_id)
                    for network_id in zone.get("networkIds", [])
                ],
            }
            for zone in zones
        ],
        "policyCount": len(policies),
        "zonePairs": [
            {
                "sourceZone": zone_names.get(source_id, source_id),
                "destinationZone": zone_names.get(destination_id, destination_id),
                "sourceZoneId": source_id,
                "destinationZoneId": destination_id,
                "policies": sorted(
                    pairs[(source_id, destination_id)], key=policy_order
                ),
            }
            for source_id, destination_id in sorted(pairs, key=pair_order)
        ],
    }


def device_summary(device: JSON, *keys: str) -> JSON:
    """Return the ID, the name, the model, and the given keys of a device."""
    return {key: device.get(key) for key in ("id", "name", "model", *keys)}


def build_site_health(
    site_id: str,
    devices: list[JSON],
    clients: list[JSON],
    pending: list[JSON],
    wans: list[JSON],
) -> JSON:
    """Summarize the state of the devices and clients of a site, and list the issues."""
    not_online = [
        device_summary(device, "state", "ipAddress")
        for device in devices
        if device.get("state") != "ONLINE"
    ]
    updatable = [
        device_summary(device, "firmwareVersion")
        for device in devices
        if device.get("firmwareUpdatable")
    ]
    versions: dict[str, Counter[str]] = {}
    for device in devices:
        if device.get("model") and device.get("firmwareVersion"):
            versions.setdefault(device["model"], Counter())[
                device["firmwareVersion"]
            ] += 1
    mismatches = {
        model: dict(counts) for model, counts in versions.items() if len(counts) > 1
    }
    # The list of pending devices is for the full console. A device with no target site
    # can go to any site.
    site_pending = [
        {key: device.get(key) for key in ("macAddress", "model", "ipAddress", "state")}
        for device in pending
        if site_id in device.get("adoptionTargetSiteIds", [site_id])
    ]

    issues = []
    if not_online:
        issues.append(f"{len(not_online)} device(s) are not online.")
    if updatable:
        issues.append(f"{len(updatable)} device(s) have a firmware update.")
    if mismatches:
        issues.append(
            f"{len(mismatches)} model(s) have different firmware versions: "
            + ", ".join(sorted(mismatches))
            + "."
        )
    if site_pending:
        issues.append(f"{len(site_pending)} device(s) wait for adoption.")

    return {
        "siteId": site_id,
        "issues": issues,
        "devices": {
            "total": len(devices),
            "byState": dict(Counter(device.get("state") for device in devices)),
            "notOnline": not_online,
            "firmwareUpdatable": updatable,
            "firmwareVersionMismatches": mismatches,
        },
        "pendingAdoption": site_pending,
        "wans": [wan.get("name") for wan in wans],
        "clients": {
            "total": len(clients),
            "byType": dict(Counter(client.get("type") for client in clients)),
        },
    }


def build_device_health(
    site_id: str, devices: list[JSON], statistics: list[JSON | Exception]
) -> JSON:
    """Combine each device with its statistics, and sort the devices that need attention first."""
    rows = []
    for device, stats in zip(devices, statistics, strict=True):
        row = device_summary(device, "state")
        if isinstance(stats, Exception):
            row["statisticsError"] = str(stats)
        else:
            row.update(
                {
                    key: stats.get(key)
                    for key in (
                        "uptimeSec",
                        "cpuUtilizationPct",
                        "memoryUtilizationPct",
                        "loadAverage1Min",
                        "loadAverage5Min",
                        "loadAverage15Min",
                        "lastHeartbeatAt",
                    )
                }
            )
            uplink = stats.get("uplink") or {}
            row["uplinkRxRateBps"] = uplink.get("rxRateBps")
            row["uplinkTxRateBps"] = uplink.get("txRateBps")
            radios = (stats.get("interfaces") or {}).get("radios")
            if radios:
                row["radios"] = radios
        rows.append({key: value for key, value in row.items() if value is not None})

    def attention(row: JSON) -> tuple[bool, float]:
        usage = max(
            row.get("cpuUtilizationPct") or 0, row.get("memoryUtilizationPct") or 0
        )
        return (row.get("state") == "ONLINE", -usage)

    return {
        "siteId": site_id,
        "deviceCount": len(devices),
        "devices": sorted(rows, key=attention),
    }


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
