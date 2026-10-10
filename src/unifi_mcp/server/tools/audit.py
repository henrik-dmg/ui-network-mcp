"""Tools that audit the configuration of a site."""

import asyncio

from fastmcp import Context, FastMCP

from unifi_mcp.client import JSON
from unifi_mcp.reports import build_unused_objects
from unifi_mcp.server.parameters import READ_ONLY, SiteId
from unifi_mcp.server.sites import client_of, resolve_site


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=READ_ONLY, tags={"read", "audit"})
    async def find_unused_objects(ctx: Context, site_id: SiteId = None) -> JSON:
        """Find the configuration objects of a site that nothing uses, and the disabled objects.

        The result lists traffic matching lists that no firewall policy uses, networks that no
        client, device, WiFi broadcast, route, or NAT rule refers to, custom firewall zones without
        networks, device tags without devices, and the disabled networks, WiFi broadcasts,
        firewall policies, ACL rules, and DNS policies. The result has only the non-empty lists.
        """
        site = await resolve_site(ctx, site_id)
        client = client_of(ctx)
        paths = {
            "networks": "networks",
            "firewallZones": "firewall/zones",
            "firewallPolicies": "firewall/policies",
            "trafficMatchingLists": "traffic-matching-lists",
            "deviceTags": "device-tags",
            "wifiBroadcasts": "wifi/broadcasts",
            "aclRules": "acl-rules",
            "dnsPolicies": "dns/policies",
        }
        lists = await asyncio.gather(
            *(client.get_all(f"/v1/sites/{site}/{path}") for path in paths.values())
        )
        resources = dict(zip(paths, lists, strict=True))
        references = await client.gather_limited(
            [
                f"/v1/sites/{site}/networks/{network['id']}/references"
                for network in resources["networks"]
            ],
            return_errors=True,
        )
        return build_unused_objects(site, resources, references)
