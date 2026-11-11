import pytest
from pydantic import ValidationError

from unifi_mcp.config import Settings

UNIFI_VARIABLES = (
    "API_KEY",
    "HOST",
    "CONSOLE_ID",
    "BASE_URL",
    "VERIFY_TLS",
    "TIMEOUT",
    "DEFAULT_SITE_ID",
    "ALLOW_WRITES",
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in UNIFI_VARIABLES:
        monkeypatch.delenv(f"UNIFI_{name}", raising=False)


def test_empty_variables_are_unset(monkeypatch):
    for name in ("HOST", "BASE_URL", "VERIFY_TLS", "DEFAULT_SITE_ID", "ALLOW_WRITES"):
        monkeypatch.setenv(f"UNIFI_{name}", "")
    monkeypatch.setenv("UNIFI_API_KEY", "key")
    monkeypatch.setenv("UNIFI_CONSOLE_ID", "console")

    settings = Settings()

    assert settings.resolved_base_url.endswith(
        "/consoles/console/proxy/network/integration"
    )
    assert (settings.verify_tls, settings.allow_writes) == (True, False)
    assert settings.default_site_id is None


def test_one_target_is_necessary(monkeypatch):
    monkeypatch.setenv("UNIFI_API_KEY", "key")
    monkeypatch.setenv("UNIFI_HOST", "")
    with pytest.raises(ValidationError, match="exactly one"):
        Settings()
