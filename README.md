# unifi-mcp

An MCP server for the UniFi Network API (integration API, version 10.6.106). The server uses [FastMCP](https://gofastmcp.com).
The API specification is in `network_v10.6.106_openapi.json`.

## Tools

All tools are read-only at this time.

| Tool | Endpoint |
|-|-|
| `get_application_info` | `GET /v1/info` |
| `list_sites` | `GET /v1/sites` |
| `list_devices`, `get_device` | `GET /v1/sites/{siteId}/devices[/{deviceId}]` |
| `get_device_statistics` | `GET /v1/sites/{siteId}/devices/{deviceId}/statistics/latest` |
| `list_pending_devices` | `GET /v1/pending-devices` |
| `list_clients`, `get_client` | `GET /v1/sites/{siteId}/clients[/{clientId}]` |
| `list_networks`, `get_network` | `GET /v1/sites/{siteId}/networks[/{networkId}]` |
| `get_network_references` | `GET /v1/sites/{siteId}/networks/{networkId}/references` |
| `list_wifi_broadcasts`, `get_wifi_broadcast` | `GET /v1/sites/{siteId}/wifi/broadcasts[/{wifiBroadcastId}]` |
| `list_wans` | `GET /v1/sites/{siteId}/wans` |
| `list_vpn_servers` | `GET /v1/sites/{siteId}/vpn/servers` |
| `list_site_to_site_tunnels` | `GET /v1/sites/{siteId}/vpn/site-to-site-tunnels` |
| `list_radius_profiles` | `GET /v1/sites/{siteId}/radius/profiles` |
| `list_device_tags` | `GET /v1/sites/{siteId}/device-tags` |
| `list_firewall_zones`, `get_firewall_zone` | `GET /v1/sites/{siteId}/firewall/zones[/{firewallZoneId}]` |
| `list_firewall_policies`, `get_firewall_policy` | `GET /v1/sites/{siteId}/firewall/policies[/{firewallPolicyId}]` |
| `get_firewall_policy_ordering` | `GET /v1/sites/{siteId}/firewall/policies/ordering` |
| `list_acl_rules`, `get_acl_rule` | `GET /v1/sites/{siteId}/acl-rules[/{aclRuleId}]` |
| `get_acl_rule_ordering` | `GET /v1/sites/{siteId}/acl-rules/ordering` |
| `list_dns_policies`, `get_dns_policy` | `GET /v1/sites/{siteId}/dns/policies[/{dnsPolicyId}]` |
| `list_traffic_matching_lists`, `get_traffic_matching_list` | `GET /v1/sites/{siteId}/traffic-matching-lists[/{trafficMatchingListId}]` |
| `get_topology` | Devices, device details, and clients, combined into one device tree |
| `get_firewall_overview` | Firewall zones and policies, grouped by zone pair, with the names of the referenced resources |

If a tool call does not include `site_id`, the server uses `UNIFI_DEFAULT_SITE_ID`.
If that variable is not set and the console has exactly one site, the server uses that site.

## Configuration

1. Create an API key in UniFi Network, in **Settings > Control Plane > Integrations**.
2. Copy `.env.example` to `.env`.
3. Set `UNIFI_API_KEY` and one of `UNIFI_HOST`, `UNIFI_CONSOLE_ID`, or `UNIFI_BASE_URL`.

## Add the server to Claude Code

```sh
claude mcp add unifi -- uv run --project /path/to/unifi-mcp unifi-mcp
```

The server reads the `.env` file in the project folder, then the `.env` file in its working directory.
A value in the environment replaces a value from a `.env` file.

## Development

```sh
uv run pytest
uv run ruff check && uv run ruff format
```
