from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from schemas.area import Area
from schemas.base import Ident, Payload
from schemas.education import Educations
from schemas.experience import Experience
from schemas.metro import Metro
from schemas.owner import Owner


class Salary(Payload):
    """`salary`, absent whenever the applicant hid it."""

    amount: Decimal | None = None
    currency: str | None = None


class TotalExperience(Payload):
    """`total_experience`, which HH reports only in whole months."""

    months: int | None = None


class Relocation(Payload):
    """`relocation`, split across three columns to stay queryable."""

    type: dict[str, Any] | None = None
    area: list[dict[str, Any]] | None = None
    district: list[dict[str, Any]] | None = None


class Resume(Payload):
    """An HH resume payload, short or full, mirrored field for field."""

    id: str
    owner: Owner
    real_id: str | None = None
    url: str | None = None
    alternate_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    platform: Ident | None = None

    title: str | None = None
    salary: Salary | None = None
    total_experience: TotalExperience | None = None
    skill_set: list[str] | None = None
    skills: str | None = None
    photo: dict[str, Any] | None = None

    area: Area | None = None
    metro: Metro | None = None
    education: Educations | None = None
    experience: list[Experience] = Field(default_factory=list)

    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    age: int | None = None
    gender: Ident | None = None
    birth_date: date | None = None
    contact: list[dict[str, Any]] | None = None

    job_search_status: dict[str, Any] | None = None
    business_trip_readiness: dict[str, Any] | None = None
    travel_time: dict[str, Any] | None = None
    resume_locale: dict[str, Any] | None = None
    relocation: Relocation | None = None

    employments: list[dict[str, Any]] | None = None
    schedules: list[dict[str, Any]] | None = None
    employment_form: list[dict[str, Any]] | None = None
    work_format: list[dict[str, Any]] | None = None
    professional_roles: list[dict[str, Any]] | None = None
    citizenship: list[dict[str, Any]] | None = None
    work_ticket: list[dict[str, Any]] | None = None
    language: list[dict[str, Any]] | None = None
    portfolio: list[dict[str, Any]] | None = None
    certificate: list[dict[str, Any]] | None = None
    site: list[dict[str, Any]] | None = None
    recommendation: list[dict[str, Any]] | None = None
    hidden_fields: list[dict[str, Any]] | None = None
    tags: list[dict[str, Any]] | None = None

    driver_license_types: list[Ident] | None = None
    has_vehicle: bool | None = None
    has_medical_book: bool | None = None
    has_self_employment: bool | None = None
