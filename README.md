# unifi-mcp

An MCP server for the UniFi Network API (integration API, version 11.0.97). The server uses [FastMCP](https://gofastmcp.com).
The API specification is in `network_v11.0.97_openapi.json`.

## Comparison with sirkirby/unifi-mcp

[sirkirby/unifi-mcp](https://github.com/sirkirby/unifi-mcp) is a larger MCP project for UniFi, with servers for UniFi Network, Protect, and Access.
The two projects use different APIs and different credentials. Thus each project is useful for different tasks.
The data about sirkirby/unifi-mcp is from November 2026.

| | This server | sirkirby/unifi-mcp |
|-|-|-|
| UniFi applications | Network | Network, Protect, and Access |
| API | Only the official integration API | Mostly the private controller API, and the integration API for some tools |
| Credentials | An API key, which can be read-only | The username and password of a local admin account without MFA. An API key alone gives only some read tools. |
| Network tools | Almost all read endpoints of the integration API, and combined report tools | 210 tools, and many of them use endpoints that the integration API does not have |
| Changes | Firewall policies, device and port actions, guest access, and Hotspot vouchers. The write tools are hidden until you set `UNIFI_ALLOW_WRITES` to `true`. | Most configuration areas. Each change shows a preview before the server applies it. |
| Remote access | The UniFi cloud connector, with `UNIFI_CONSOLE_ID` | A Cloudflare Worker and a relay on the local network |
| Size | One small Python package | A monorepo with MCP servers, a REST and GraphQL server, a relay, and plugins |

Use this server if:

- You want to give the agent an API key, not an admin password. You can revoke an API key at any time, and a read-only key cannot change the network.
- You want a documented API. Ubiquiti publishes a specification for each version of the integration API. The private API has no public documentation and can change with a firmware update.
- You want remote access through the UniFi cloud connector, without a relay or another service.
- You want a server that is small enough to read and examine in full.
- You ask more questions about the network than you make changes to it.

Use sirkirby/unifi-mcp if:

- You use UniFi Protect or UniFi Access.
- You must change settings that the integration API does not have, for example port forwards, static routes, NAT rules, QoS rules, or VPN clients.
- You need history data, for example events, alarms, traffic statistics, DPI traffic, or traffic flows.
- You want Claude Code plugins with agent skills for frequent tasks.

You can use both servers in the same MCP client. Give each server a different name in the MCP configuration.

## Tools

Most tools are read-only. The server adds the [write tools](#write-tools) only if `UNIFI_ALLOW_WRITES` is `true`.

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
| `list_lags`, `get_lag` | `GET /v1/sites/{siteId}/switching/lags[/{lagId}]` |
| `list_mc_lag_domains`, `get_mc_lag_domain` | `GET /v1/sites/{siteId}/switching/mc-lag-domains[/{mcLagDomainId}]` |
| `list_switch_stacks`, `get_switch_stack` | `GET /v1/sites/{siteId}/switching/switch-stacks[/{switchStackId}]` |
| `list_vouchers`, `get_voucher` | `GET /v1/sites/{siteId}/hotspot/vouchers[/{voucherId}]` |
| `list_firewall_zones`, `get_firewall_zone` | `GET /v1/sites/{siteId}/firewall/zones[/{firewallZoneId}]` |
| `list_firewall_policies`, `get_firewall_policy` | `GET /v1/sites/{siteId}/firewall/policies[/{firewallPolicyId}]` |
| `get_firewall_policy_ordering` | `GET /v1/sites/{siteId}/firewall/policies/ordering` |
| `list_acl_rules`, `get_acl_rule` | `GET /v1/sites/{siteId}/acl-rules[/{aclRuleId}]` |
| `get_acl_rule_ordering` | `GET /v1/sites/{siteId}/acl-rules/ordering` |
| `list_dns_policies`, `get_dns_policy` | `GET /v1/sites/{siteId}/dns/policies[/{dnsPolicyId}]` |
| `list_traffic_matching_lists`, `get_traffic_matching_list` | `GET /v1/sites/{siteId}/traffic-matching-lists[/{trafficMatchingListId}]` |
| `list_dpi_applications` | `GET /v1/dpi/applications` |
| `list_dpi_categories` | `GET /v1/dpi/categories` |
| `get_topology` | Devices, device details, and clients, combined into one device tree |
| `get_firewall_overview` | Firewall zones and policies, grouped by zone pair, with the names of the referenced resources |
| `get_site_health` | Devices, clients, pending devices, and WAN interfaces, combined into one health summary with a list of issues |
| `get_device_health` | The latest statistics of all devices, with the device that needs most attention first |
| `get_wifi_overview` | WiFi broadcasts, the radios of each access point, and the wireless clients, with channel conflicts and radios with many retries |
| `get_switch_port_report` | The ports of each device with ports: speed, PoE state, and wired clients, with slow ports and limited PoE power |
| `get_network_map` | All networks by VLAN ID, with the subnet, the DHCP mode, the firewall zone, and the WiFi broadcasts of each network |
| `get_client_summary` | The clients by type, by access type, and by uplink device, and the newest clients |
| `find_client` | The clients whose name, IP address, or MAC address contains a search text |
| `get_voucher_summary` | The Hotspot vouchers by status, the vouchers that expire soon, and the fully used vouchers, without the codes |
| `find_unused_objects` | Unused traffic matching lists, networks, firewall zones, and device tags, and the disabled objects |

If a tool call does not include `site_id`, the server uses `UNIFI_DEFAULT_SITE_ID`.
If that variable is not set and the console has exactly one site, the server uses that site.

### Write tools

| Tool | Endpoint |
|-|-|
| `create_firewall_policy` | `POST /v1/sites/{siteId}/firewall/policies` |
| `update_firewall_policy` | `PATCH` or `GET` and `PUT /v1/sites/{siteId}/firewall/policies/{firewallPolicyId}` |
| `delete_firewall_policy` | `DELETE /v1/sites/{siteId}/firewall/policies/{firewallPolicyId}` |
| `reorder_firewall_policies` | `PUT /v1/sites/{siteId}/firewall/policies/ordering` |
| `adopt_device` | `POST /v1/sites/{siteId}/devices` |
| `remove_device` | `DELETE /v1/sites/{siteId}/devices/{deviceId}` |
| `restart_device` | `POST /v1/sites/{siteId}/devices/{deviceId}/actions` |
| `power_cycle_port` | `POST /v1/sites/{siteId}/devices/{deviceId}/interfaces/ports/{portIdx}/actions` |
| `authorize_guest`, `unauthorize_guest` | `POST /v1/sites/{siteId}/clients/{clientId}/actions` |
| `create_vouchers` | `POST /v1/sites/{siteId}/hotspot/vouchers` |
| `delete_voucher` | `DELETE /v1/sites/{siteId}/hotspot/vouchers/{voucherId}` |
| `delete_vouchers` | `DELETE /v1/sites/{siteId}/hotspot/vouchers` with a filter |

`update_firewall_policy` changes only the given fields. If the only changes are `logging_enabled` or `report_flow_enabled`, it sends a `PATCH` request. For all other changes, it reads the policy and sends the full policy with the changes.
The server checks each policy body against typed models before it sends the request.

Caution: Examine each write tool call before you approve it. A wrong firewall policy can block the access to the console. `remove_device` resets an online device to the factory settings.

## Configuration

Create an API key in UniFi Network, in **Settings > Control Plane > Integrations**.
The server reads its settings from these environment variables:

| Variable | Description |
|-|-|
| `UNIFI_API_KEY` | Required. The API key. |
| `UNIFI_HOST` | The IP address or hostname of a local console. |
| `UNIFI_CONSOLE_ID` | The console ID from unifi.ui.com. The server then uses the cloud connector. |
| `UNIFI_BASE_URL` | Any other URL that ends in `/proxy/network/integration`. |
| `UNIFI_VERIFY_TLS` | Optional, default `true`. Local consoles usually use a self-signed certificate. Set this to `false` only on a network that you trust. |
| `UNIFI_TIMEOUT` | Optional, default `30`. The request timeout in seconds. |
| `UNIFI_DEFAULT_SITE_ID` | Optional. The site to use when a tool call does not include `site_id`. |
| `UNIFI_ALLOW_WRITES` | Optional, default `false`. Set this to `true` to add the write tools. The API key must have write access. |

Set exactly one of `UNIFI_HOST`, `UNIFI_CONSOLE_ID`, or `UNIFI_BASE_URL`.

## Add the server to Claude Code

You do not have to clone the repository. `uvx` installs the server from GitHub and starts it:

```sh
claude mcp add unifi \
  -e UNIFI_API_KEY=your-api-key \
  -e UNIFI_HOST=192.168.1.1 \
  -- uvx --from git+https://github.com/henrik-dmg/unifi-mcp unifi-mcp
```

For Claude Desktop and other MCP hosts, add this entry to the MCP configuration file:

```json
{
  "mcpServers": {
    "unifi": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/henrik-dmg/unifi-mcp", "unifi-mcp"],
      "env": {
        "UNIFI_API_KEY": "your-api-key",
        "UNIFI_HOST": "192.168.1.1"
      }
    }
  }
}
```

To get a new version of the server, run `uvx --refresh --from git+https://github.com/henrik-dmg/unifi-mcp unifi-mcp` one time.

### Run from a clone

To use a local clone, give its path to `uv run --project`:

```sh
claude mcp add unifi \
  -e UNIFI_API_KEY=your-api-key \
  -e UNIFI_HOST=192.168.1.1 \
  -- uv run --project /path/to/unifi-mcp unifi-mcp
```

`uv run` installs the clone in editable mode. Thus the server uses your changes to the code when it starts again, and you do not have to reinstall it.

## Development

```sh
uv run pytest
uv run ruff check && uv run ruff format
```
