from typing import Any

from pydantic import Field

from schemas.base import Payload


class Education(Payload):
    """One study entry, the same shape in all four HH buckets."""

    id: str | None = None
    name: str | None = None
    organization: str | None = None
    result: str | None = None
    year: int | None = None
    university_acronym: str | None = None
    name_id: str | None = None
    organization_id: str | None = None
    result_id: str | None = None
    education_level: dict[str, Any] | None = None


class Educations(Payload):
    """The `education` block; bucket names match EducationType values."""

    level: dict[str, Any] | None = None
    primary: list[Education] = Field(default_factory=list)
    additional: list[Education] = Field(default_factory=list)
    attestation: list[Education] = Field(default_factory=list)
    elementary: list[Education] = Field(default_factory=list)
