from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.enums import Gender, choice

if TYPE_CHECKING:
    from models.resume import Resume


class Owner(Base):
    """The person behind the resumes, keyed by HH `owner.id`."""

    __tablename__ = "owner"

    hh_owner_id: Mapped[str] = mapped_column(String(32), unique=True)
    first_name: Mapped[str | None]
    last_name: Mapped[str | None]
    middle_name: Mapped[str | None]
    age: Mapped[int | None] = mapped_column(SmallInteger)
    gender: Mapped[Gender | None] = mapped_column(choice(Gender, "gender"))
    birth_date: Mapped[date | None]
    contact: Mapped[list[dict[str, Any]] | None]

    resumes: Mapped[list[Resume]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
