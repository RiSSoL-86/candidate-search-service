from decimal import Decimal
from typing import Any

from schemas.base import Payload


class Metro(Payload):
    """`metro` on a resume, with its line left as a nested object."""

    id: str
    name: str
    lat: Decimal | None = None
    lng: Decimal | None = None
    order: int | None = None
    line: dict[str, Any] | None = None
