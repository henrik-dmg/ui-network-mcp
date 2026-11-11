"""Redaction of the secrets in API responses, so that the secrets do not get to the agent."""

from typing import Any

REDACTED = "***REDACTED***"
# The API uses these keys for secrets. In version 11.0.97, the only secrets are the WiFi
# passphrases of the WPA2, WPA2/WPA3, and WPA3 personal broadcasts and their pre-shared keys.
SECRET_KEYS = frozenset({"passphrase"})


def redact(value: Any) -> Any:
    """Return a copy of a JSON value that has REDACTED in place of each secret."""
    if isinstance(value, dict):
        return {
            key: REDACTED if key in SECRET_KEYS and item is not None else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def contains_redacted(value: Any) -> bool:
    """Return True if REDACTED is a value anywhere in a JSON value."""
    if isinstance(value, dict):
        return any(contains_redacted(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_redacted(item) for item in value)
    return value == REDACTED
