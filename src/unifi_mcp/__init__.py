import sys


def main() -> None:
    from pydantic import ValidationError

    from unifi_mcp.server import create_server

    try:
        server = create_server()
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(map(str, e['loc'])) or 'settings'}: {e['msg']}"
            for e in error.errors()
        )
        sys.exit(
            f"unifi-mcp: invalid configuration ({problems}). Set the UNIFI_* variables in .env or in the environment."
        )
    server.run()
