from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from css_models.base import Base


class Area(Base):
    """Shared geography card, referenced by both a resume and a job."""

    __tablename__ = "area"

    hh_area_id: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str]
    hh_url: Mapped[str | None]
