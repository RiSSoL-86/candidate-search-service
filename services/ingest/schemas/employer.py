from typing import Any

from schemas.base import Payload


class Employer(Payload):
    """`experience[].employer`, present only for verified companies."""

    id: str | None = None
    name: str
    url: str | None = None
    alternate_url: str | None = None
    logo_urls: dict[str, Any] | None = None
