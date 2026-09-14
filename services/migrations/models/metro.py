from decimal import Decimal
from typing import Any

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Metro(Base):
    """Shared metro station card with its line kept as a nested object."""

    __tablename__ = "metro"

    hh_metro_id: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str]
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    hh_order: Mapped[int | None] = mapped_column(Integer)
    line: Mapped[dict[str, Any] | None]
