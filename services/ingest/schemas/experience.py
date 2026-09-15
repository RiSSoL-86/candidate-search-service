from datetime import date
from typing import Any

from schemas.area import Area
from schemas.base import Payload
from schemas.employer import Employer


class Experience(Payload):
    """One job as it was listed in this download."""

    id: str | None = None
    start: date | None = None
    end: date | None = None
    company: str | None = None
    company_id: str | None = None
    company_url: str | None = None
    employer: Employer | None = None
    position: str | None = None
    description: str | None = None
    area: Area | None = None
    industry: dict[str, Any] | None = None
    industries: list[dict[str, Any]] | None = None
