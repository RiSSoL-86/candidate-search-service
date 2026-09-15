from typing import Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from css_models.base import Base


class Employer(Base):
    """Shared card for the `employer` object of an experience entry."""

    __tablename__ = "employer"

    hh_employer_id: Mapped[str | None] = mapped_column(String(32), unique=True)
    name: Mapped[str]
    hh_url: Mapped[str | None]
    hh_alternate_url: Mapped[str | None]
    logo_urls: Mapped[dict[str, Any] | None]
