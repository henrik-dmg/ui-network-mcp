from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from pydantic_core import to_jsonable_python

from ui_network_mcp.client import JSON


class ApiModel(BaseModel):
    """A part of a request body. The JSON schema uses the camelCase names of the API."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_alias=True,
        validate_by_name=True,
        extra="forbid",
    )


def request_body(**fields: Any) -> JSON:
    """Make a request body from snake_case fields. The body does not include None values."""
    return to_jsonable_python(
        {to_camel(name): value for name, value in fields.items() if value is not None},
        by_alias=True,
        exclude_none=True,
    )
