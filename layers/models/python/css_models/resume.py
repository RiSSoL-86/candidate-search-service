import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    ARRAY,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    desc,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from css_models.area import Area
from css_models.base import Base
from css_models.enums import DriverLicenseType, ResumeType, choice
from css_models.metro import Metro
from css_models.owner import Owner

if TYPE_CHECKING:
    from css_models.education import Education
    from css_models.experience import Experience


class Resume(Base):
    """One download of a resume, mirroring the HH payload field for field."""

    __tablename__ = "resume"
    __table_args__ = (
        Index(
            "ix_resume_owner_history",
            "owner_id",
            desc("downloaded_at"),
            desc("id"),
        ),
        UniqueConstraint(
            "s3_bucket",
            "s3_key",
            "s3_version_id",
            postgresql_nulls_not_distinct=True,
        ),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(Owner.id))
    resume_type: Mapped[ResumeType] = mapped_column(
        choice(ResumeType, "resume_type")
    )
    downloaded_at: Mapped[datetime]

    s3_bucket: Mapped[str] = mapped_column(String(63))
    s3_key: Mapped[str] = mapped_column(String(1024))
    s3_version_id: Mapped[str | None] = mapped_column(String(1024))

    hh_resume_id: Mapped[str] = mapped_column(String(64), index=True)
    hh_real_id: Mapped[str | None] = mapped_column(String(32))
    hh_url: Mapped[str | None]
    hh_alternate_url: Mapped[str | None]
    hh_created_at: Mapped[datetime | None]
    hh_updated_at: Mapped[datetime | None]
    platform_id: Mapped[str | None] = mapped_column(String(32))

    title: Mapped[str | None]
    salary_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    salary_currency: Mapped[str | None] = mapped_column(String(8))
    total_experience_months: Mapped[int | None] = mapped_column(Integer)
    skill_set: Mapped[list[str] | None]
    skills: Mapped[str | None]
    photo: Mapped[dict[str, Any] | None]

    area_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(Area.id), index=True
    )
    metro_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(Metro.id), index=True
    )

    education_level: Mapped[dict[str, Any] | None]
    job_search_status: Mapped[dict[str, Any] | None]
    business_trip_readiness: Mapped[dict[str, Any] | None]
    travel_time: Mapped[dict[str, Any] | None]
    resume_locale: Mapped[dict[str, Any] | None]
    relocation_type: Mapped[dict[str, Any] | None]
    relocation_area: Mapped[list[dict[str, Any]] | None]
    relocation_district: Mapped[list[dict[str, Any]] | None]

    employments: Mapped[list[dict[str, Any]] | None]
    schedules: Mapped[list[dict[str, Any]] | None]
    employment_form: Mapped[list[dict[str, Any]] | None]
    work_format: Mapped[list[dict[str, Any]] | None]
    professional_roles: Mapped[list[dict[str, Any]] | None]
    citizenship: Mapped[list[dict[str, Any]] | None]
    work_ticket: Mapped[list[dict[str, Any]] | None]
    language: Mapped[list[dict[str, Any]] | None]
    portfolio: Mapped[list[dict[str, Any]] | None]
    certificate: Mapped[list[dict[str, Any]] | None]
    site: Mapped[list[dict[str, Any]] | None]
    recommendation: Mapped[list[dict[str, Any]] | None]
    hidden_fields: Mapped[list[dict[str, Any]] | None]
    tags: Mapped[list[dict[str, Any]] | None]

    driver_license_types: Mapped[list[DriverLicenseType] | None] = (
        mapped_column(
            ARRAY(
                choice(
                    DriverLicenseType, "driver_license_type", constraint=False
                )
            ),
        )
    )
    has_vehicle: Mapped[bool | None] = mapped_column(Boolean)
    has_medical_book: Mapped[bool | None] = mapped_column(Boolean)
    has_self_employment: Mapped[bool | None] = mapped_column(Boolean)

    owner: Mapped[Owner] = relationship(back_populates="resumes")
    area: Mapped[Area | None] = relationship()
    metro: Mapped[Metro | None] = relationship()
    experiences: Mapped[list[Experience]] = relationship(
        back_populates="resume",
        cascade="all, delete-orphan",
    )
    educations: Mapped[list[Education]] = relationship(
        back_populates="resume",
        cascade="all, delete-orphan",
    )
