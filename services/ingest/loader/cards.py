import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

import schemas
from css_models import Area, Employer, Metro, Owner
from css_models.base import Base
from loader.mapper import ResumeMapper


class CardWriter:
    """Writes the rows many resumes share and hands back their ids."""

    def __init__(self, mapper: ResumeMapper) -> None:
        self._mapper = mapper

    def owner(self, session: Session, resume: schemas.Resume) -> uuid.UUID:
        """Every resume has an owner, so this id is never optional."""
        return self._write(
            session=session,
            model=Owner,
            key="hh_owner_id",
            values=self._mapper.owner(resume=resume),
        )

    def area(
        self, session: Session, area: schemas.Area | None
    ) -> uuid.UUID | None:
        """Both the resume and each job may name a city, or neither may."""
        if area is None:
            return None

        return self._write(
            session=session,
            model=Area,
            key="hh_area_id",
            values=self._mapper.area(area=area),
        )

    def metro(
        self, session: Session, metro: schemas.Metro | None
    ) -> uuid.UUID | None:
        """Only applicants in a city with a metro have this block."""
        if metro is None:
            return None

        return self._write(
            session=session,
            model=Metro,
            key="hh_metro_id",
            values=self._mapper.metro(metro=metro),
        )

    def employer(
        self, session: Session, employer: schemas.Employer | None
    ) -> uuid.UUID | None:
        """Only a verified employer has an id, and only that one is shared."""
        if employer is None or employer.id is None:
            return None

        return self._write(
            session=session,
            model=Employer,
            key="hh_employer_id",
            values=self._mapper.employer(employer=employer),
        )

    def _write(
        self,
        session: Session,
        model: type[Base],
        key: str,
        values: dict[str, Any],
    ) -> uuid.UUID:
        """Insert the card once and return its id on every later call."""
        statement = (
            insert(model)
            .values(**values)
            .on_conflict_do_nothing(index_elements=[key])
            .returning(model.id)
        )
        inserted: uuid.UUID | None = session.execute(
            statement
        ).scalar_one_or_none()
        if inserted is not None:
            return inserted

        # Someone wrote this card before us, so we only need to look it up.
        found: uuid.UUID = session.execute(
            select(model.id).where(getattr(model, key) == values[key])
        ).scalar_one()
        return found
