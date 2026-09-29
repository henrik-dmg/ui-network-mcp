# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```sh
uv run pytest                                   # all tests
uv run pytest tests/test_server.py::test_name   # one test
uv run ruff check && uv run ruff format         # lint and format
uv run unifi-mcp                                # start the server (stdio), needs a valid .env
```

## Architecture

This project is a FastMCP server for the UniFi Network integration API, version 10.6.106. All tools are read-only. The full API specification is in `network_v10.6.106_openapi.json`. Search that file for an endpoint schema before you add a tool. Do not read the whole file, because it is large.

The package in `src/unifi_mcp/` has three layers:

- `config.py`: `Settings` (pydantic-settings) reads the `UNIFI_*` variables. The user must set exactly one of `UNIFI_HOST`, `UNIFI_CONSOLE_ID`, or `UNIFI_BASE_URL`. `resolved_base_url` makes the local-console URL or the cloud-connector URL from that value. The settings read the `.env` file of the project first, then the `.env` file of the working directory, because MCP hosts do not start the server in the project folder.
- `client.py`: `UniFiClient` is a thin wrapper around `httpx.AsyncClient`. It removes `None` query parameters. It changes all HTTP errors and transport errors into `UniFiAPIError`, a subclass of `ToolError`, so that FastMCP sends the message to the MCP client. `get_all` follows the pagination (page size 200). `gather_limited` sends parallel requests with a semaphore.
- `server.py`: `build_server(client_factory, default_site_id)` defines all tools as closures inside the function. The lifespan creates the client and puts it in `ctx.lifespan_context`. `create_server()` is the production entry point, and `main()` in `__init__.py` calls it.

Patterns in `server.py` to follow when you add a tool:

- Use the `SiteId`, `Filter`, `Limit`, and `Offset` annotated types for parameters.
- Use the `site_page` and `site_item` helpers for site-scoped endpoints. They call `resolve_site`, which uses the given `site_id`, then the configured default, then the only site of the console. `resolve_site` keeps the result of the lookup in the lifespan context.
- Give each tool `annotations=READ_ONLY` and a `tags` set.
- `get_topology` is a combined tool. It reads all devices, the details of each device, and all clients. The pure function `build_topology` then makes the tree from the `uplink.deviceId` of each device.

## Tests

The tests use `respx` to mock the HTTP API at `BASE` and the in-memory FastMCP `Client` to call tools. `make_server()` calls `build_server` with a client factory that does not need settings. `pytest-asyncio` runs in auto mode, so async tests need no marker.

`test_tools_are_read_only` checks the number of tools. Update that number when you add or remove a tool. Also update the tool table in `README.md`.

## Writing style

The README, docstrings, comments, and error messages use Simplified Technical English: short sentences, active voice, no contractions. Keep this style in new text.
