from datetime import datetime

from pydantic import Field

from css_models.enums import ResumeType
from schemas.base import Payload


class Source(Payload):
    """Where the caller took the JSON from, kept as the resume provenance."""

    bucket: str = Field(max_length=63)
    key: str = Field(max_length=1024)
    version_id: str | None = Field(default=None, max_length=1024)
    downloaded_at: datetime
    resume_type: ResumeType
