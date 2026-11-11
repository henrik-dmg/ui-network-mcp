# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```sh
uv run pytest                                   # all tests
uv run pytest tests/test_server.py::test_name   # one test
uv run ruff check && uv run ruff format         # lint and format
uv run unifi-mcp                                # start the server (stdio), needs the UNIFI_* variables
claude plugin validate .                        # check the plugin and the marketplace manifests
claude --plugin-dir . plugin details unifi      # show the skills and their token cost
```

## Plugin

The repository root is also a Claude Code plugin (`unifi`) and a marketplace (`unifi-mcp`), in `.claude-plugin/`. `plugin.json` declares the options (`userConfig`) and the MCP server. The MCP server is inline in `plugin.json`, because a `.mcp.json` at the root would also be a project MCP server for each person who opens this repository. The server starts with `uv run --project ${CLAUDE_PLUGIN_ROOT}`, so the server always has the same version as the skills. An unset option gives an empty environment variable, which `Settings` ignores.

The skills in `skills/` name the tools and the fields of the tool results. When you rename a tool or a result field, update the skills. Keep the `version` in `plugin.json` equal to the version in `pyproject.toml`.

## Architecture

This project is a FastMCP server for the UniFi Network integration API, version 11.0.97. Most tools are read-only. The write tools have the `write` tag, and `build_server` hides them unless `allow_writes` is true (`UNIFI_ALLOW_WRITES`). The full API specification is in `network_v11.0.97_openapi.json`. Search that file for an endpoint schema before you add a tool. Do not read the whole file, because it is large.

The package in `src/unifi_mcp/` has these layers. Each file holds one type or one group of related functions:

- `config.py`: `Settings` (pydantic-settings) reads the `UNIFI_*` variables. The user must set exactly one of `UNIFI_HOST`, `UNIFI_CONSOLE_ID`, or `UNIFI_BASE_URL`. `resolved_base_url` makes the local-console URL or the cloud-connector URL from that value. The settings come only from the environment. The server does not read a `.env` file, because MCP hosts give the settings as environment variables.
- `client/`: `UniFiClient` (`unifi_client.py`) is a thin wrapper around `httpx.AsyncClient`. It removes `None` query parameters. It changes all HTTP errors and transport errors into `UniFiAPIError` (`errors.py`), a subclass of `ToolError`, so that FastMCP sends the message to the MCP client. `get_all` follows the pagination (page size 200). `gather_limited` sends parallel requests with a semaphore. `post`, `put`, and `patch` remove `None` keys from the body. The client replaces each secret in a response with `***REDACTED***` (`redaction.py`), and refuses a write body that contains this placeholder. A 401 or 403 error on a write request adds a hint about the write access of the API key. The package `__init__.py` exports `JSON`, `MAX_PAGE_SIZE`, `UniFiAPIError`, and `UniFiClient`.
- `server/`: `app.py` has `build_server(client_factory, default_site_id, allow_writes)` and `create_server()`. The lifespan creates the client and puts it in `ctx.lifespan_context`. `create_server()` is the production entry point, and `main()` in `__init__.py` calls it. `parameters.py` has the shared parameter types, `WRITE_TAG`, and the annotations `READ_ONLY`, `ADDITIVE_WRITE`, and `DESTRUCTIVE_WRITE`. `sites.py` has `client_of`, `resolve_site`, `site_page`, and `site_item`.
- `server/tools/`: one module for each tag. Each module has a `register(mcp)` function that defines its tools as closures. `tools/__init__.py` calls each `register` function in `register_all`.
- `models/`: pydantic models for the request bodies of the write tools. `ApiModel` uses the camelCase API names as aliases and forbids unknown keys, so an agent can copy fields from a GET result. `request_body(**fields)` makes a body without `None` values. The specification is wrong about protocol names: the console uses the uppercase keys of the discriminator mapping (`TCP`, `ICMPV6`), not the lowercase enum.
- `reports/`: pure functions that make one summary from many API responses, for the combined tools. One file for each report.

Patterns to follow when you add a tool:

- Put the tool in the `server/tools/` module of its tag. For a new tag, add a module and add it to `register_all`.
- Use the `SiteId`, `Filter`, `Limit`, and `Offset` annotated types for parameters.
- Use the `site_page` and `site_item` helpers for site-scoped endpoints. They call `resolve_site`, which uses the given `site_id`, then the configured default, then the only site of the console. `resolve_site` keeps the result of the lookup in the lifespan context.
- Give each tool `annotations=READ_ONLY` and a `tags` set.
- `get_topology` is a combined tool. It reads all devices, the details of each device, and all clients. The pure function `build_topology` in `reports/topology.py` then makes the tree from the `uplink.deviceId` of each device.
- A combined tool reads only the data it needs. For example, `get_wifi_overview` and `get_switch_port_report` read the details only of the devices whose `interfaces` list includes `radios` or `ports`. A combined tool that reads statistics or references for each item uses `gather_limited(..., return_errors=True)`, so that one failed item does not stop the report.

Patterns to follow when you add a write tool:

- Give the tool the `WRITE_TAG` tag and the `ADDITIVE_WRITE` or `DESTRUCTIVE_WRITE` annotation.
- Model a nested body in `models/` with discriminated unions. For a flat body, give the fields as tool parameters with `Field` constraints, and make the body with `request_body`. See `create_vouchers`. Check the models against the real objects of a console: each GET result must parse, and `request_body` must give back the same JSON. A read-only API key is sufficient for this check.
- A PUT endpoint needs the full object. An update tool takes optional fields, reads the object, removes `id`, `index`, and `metadata`, adds the changes, and sends the result. See `update_firewall_policy`. An object with a secret, such as a WiFi broadcast with a passphrase, needs a read without redaction for this step.
- FastMCP inlines each `$ref` of a tool schema. Thus large models make a large schema: `create_firewall_policy` has about 48 KB.

## Tests

The tests use `respx` to mock the HTTP API at `BASE` and the in-memory FastMCP `Client` to call tools. `make_server()` calls `build_server` with a client factory that does not need settings. `pytest-asyncio` runs in auto mode, so async tests need no marker.

`test_tools_are_read_only` checks the number of read-only tools, and `test_write_tools_need_allow_writes` checks the number of all tools. Update these numbers when you add or remove a tool. Also update the tool table in `README.md`.

## Writing style

The README, docstrings, comments, and error messages use Simplified Technical English: short sentences, active voice, no contractions. Keep this style in new text.
