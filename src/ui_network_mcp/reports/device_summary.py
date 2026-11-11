from ui_network_mcp.client import JSON


def device_summary(device: JSON, *keys: str) -> JSON:
    """Return the ID, the name, the model, and the given keys of a device."""
    return {key: device.get(key) for key in ("id", "name", "model", *keys)}
