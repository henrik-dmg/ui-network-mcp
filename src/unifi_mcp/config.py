from pathlib import Path
from typing import Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CLOUD_CONNECTOR_URL = (
    "https://api.ui.com/v1/connector/consoles/{console_id}/proxy/network/integration"
)
LOCAL_CONSOLE_URL = "https://{host}/proxy/network/integration"

# MCP hosts such as Claude Desktop do not start the server in the project folder.
# Thus the server reads the .env file of the project, then the .env file of the
# working directory. A value in the second file replaces a value in the first file.
PROJECT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Connection settings, read from UNIFI_* environment variables or a .env file."""

    model_config = SettingsConfigDict(
        env_prefix="UNIFI_", env_file=(PROJECT_ENV_FILE, ".env"), extra="ignore"
    )

    api_key: SecretStr
    # Set exactly one of these three. The host is the IP address or hostname of a local console.
    host: str | None = None
    console_id: str | None = None
    base_url: str | None = None

    # Local consoles usually use a self-signed certificate.
    verify_tls: bool = True
    timeout: float = 30.0
    default_site_id: str | None = None
    # The server adds the tools that change the network only if this value is true.
    allow_writes: bool = False

    @model_validator(mode="after")
    def _check_target(self) -> Self:
        targets = [
            value for value in (self.host, self.console_id, self.base_url) if value
        ]
        if len(targets) != 1:
            raise ValueError(
                "Set exactly one of UNIFI_HOST, UNIFI_CONSOLE_ID, or UNIFI_BASE_URL."
            )
        return self

    @property
    def resolved_base_url(self) -> str:
        if self.base_url:
            return self.base_url.rstrip("/")
        if self.console_id:
            return CLOUD_CONNECTOR_URL.format(console_id=self.console_id)
        return LOCAL_CONSOLE_URL.format(host=self.host)
