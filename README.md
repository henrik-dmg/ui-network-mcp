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
| `list_wifi_broadcasts` | `GET /v1/sites/{siteId}/wifi/broadcasts` |
| `list_wans` | `GET /v1/sites/{siteId}/wans` |
| `get_topology` | Devices, device details, and clients, combined into one device tree |

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
