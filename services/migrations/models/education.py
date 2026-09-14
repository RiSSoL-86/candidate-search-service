import uuid
from typing import Any

from sqlalchemy import ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.enums import EducationType, choice
from models.resume import Resume


class Education(Base):
    """One study entry as it was listed in a single resume download."""

    __tablename__ = "education"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(Resume.id, ondelete="CASCADE"),
        index=True,
    )
    hh_education_id: Mapped[str | None] = mapped_column(String(32))
    education_type: Mapped[EducationType] = mapped_column(
        choice(EducationType, "education_type"),
    )
    education_level: Mapped[dict[str, Any] | None]
    name: Mapped[str | None]
    organization: Mapped[str | None]
    result: Mapped[str | None]
    year: Mapped[int | None] = mapped_column(SmallInteger)
    university_acronym: Mapped[str | None]
    hh_name_id: Mapped[str | None] = mapped_column(String(32))
    hh_organization_id: Mapped[str | None] = mapped_column(String(32))
    hh_result_id: Mapped[str | None] = mapped_column(String(32))

    resume: Mapped[Resume] = relationship(back_populates="educations")
