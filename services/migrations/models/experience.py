import uuid
from datetime import date
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.area import Area
from models.base import Base
from models.employer import Employer
from models.resume import Resume


class Experience(Base):
    """One job as it was listed in a single resume download."""

    __tablename__ = "experience"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(Resume.id, ondelete="CASCADE"),
        index=True,
    )
    hh_experience_id: Mapped[str | None] = mapped_column(String(32))
    company: Mapped[str | None]
    hh_company_id: Mapped[str | None] = mapped_column(String(32))
    company_url: Mapped[str | None]
    employer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(Employer.id),
        index=True,
    )
    position: Mapped[str | None]
    start_date: Mapped[date | None]
    end_date: Mapped[date | None]
    description: Mapped[str | None]
    area_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(Area.id), index=True
    )
    industry: Mapped[dict[str, Any] | None]
    industries: Mapped[list[dict[str, Any]] | None]

    resume: Mapped[Resume] = relationship(back_populates="experiences")
    employer: Mapped[Employer | None] = relationship()
    area: Mapped[Area | None] = relationship()
