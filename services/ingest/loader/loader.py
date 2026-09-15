import uuid

from aws_lambda_powertools import Logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

import schemas
from css_models import Education, Experience, Resume
from css_models.enums import EducationType
from loader.cards import CardWriter
from loader.mapper import ResumeMapper


class Loader:
    """Writes one downloaded HH resume into the candidates database."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        cards: CardWriter,
        mapper: ResumeMapper,
        logger: Logger,
    ) -> None:
        self._session_factory = session_factory
        self._cards = cards
        self._mapper = mapper
        self._logger = logger

    def execute(self, envelope: schemas.Envelope) -> schemas.Result:
        """Shared cards first, then the snapshot, then the rows under it."""
        source, resume = envelope.source, envelope.resume
        self._logger.info(
            "Loading resume",
            s3_key=source.key,
            hh_resume_id=resume.id,
            resume_type=source.resume_type,
        )

        with self._session_factory() as session, session.begin():
            owner_id = self._cards.owner(session=session, resume=resume)
            area_id = self._cards.area(session=session, area=resume.area)
            metro_id = self._cards.metro(session=session, metro=resume.metro)
            self._logger.info(
                "Cards written",
                hh_resume_id=resume.id,
                owner_id=str(owner_id),
                area_id=str(area_id),
                metro_id=str(metro_id),
            )

            values = self._mapper.resume(
                source=source,
                resume=resume,
                owner_id=owner_id,
                area_id=area_id,
                metro_id=metro_id,
            )

            resume_id = self._resume(session=session, values=values)
            if resume_id is None:
                stored = self._stored(session=session, source=source)
                self._logger.info(
                    "Resume already loaded",
                    s3_key=source.key,
                    hh_resume_id=resume.id,
                    resume_id=str(stored),
                )
                return schemas.Result(resume_id=stored, created=False)

            experiences = self._experiences(
                session=session,
                resume_id=resume_id,
                entries=resume.experience,
            )
            educations = self._educations(
                session=session,
                resume_id=resume_id,
                education=resume.education,
            )

            self._logger.info(
                "Resume loaded",
                s3_key=source.key,
                hh_resume_id=resume.id,
                resume_id=str(resume_id),
                experiences=experiences,
                educations=educations,
            )
            return schemas.Result(resume_id=resume_id, created=True)

    def _resume(
        self, session: Session, values: dict[str, object]
    ) -> uuid.UUID | None:
        """Write the snapshot, or answer None when we already hold it."""
        statement = (
            insert(Resume)
            .values(**values)
            .on_conflict_do_nothing(
                index_elements=["s3_bucket", "s3_key", "s3_version_id"]
            )
            .returning(Resume.id)
        )
        written: uuid.UUID | None = session.execute(
            statement
        ).scalar_one_or_none()
        return written

    def _stored(self, session: Session, source: schemas.Source) -> uuid.UUID:
        """Find the snapshot an earlier delivery of this message wrote."""
        found: uuid.UUID = session.execute(
            select(Resume.id).where(
                Resume.s3_bucket == source.bucket,
                Resume.s3_key == source.key,
                Resume.s3_version_id == source.version_id,
            )
        ).scalar_one()
        return found

    def _experiences(
        self,
        session: Session,
        resume_id: uuid.UUID,
        entries: list[schemas.Experience],
    ) -> int:
        """Jobs belong to this download only, so they are always fresh rows."""
        for entry in entries:
            session.execute(
                insert(Experience).values(
                    **self._mapper.experience(
                        resume_id=resume_id,
                        entry=entry,
                        employer_id=self._cards.employer(
                            session=session, employer=entry.employer
                        ),
                        area_id=self._cards.area(
                            session=session, area=entry.area
                        ),
                    )
                )
            )

        return len(entries)

    def _educations(
        self,
        session: Session,
        resume_id: uuid.UUID,
        education: schemas.Educations | None,
    ) -> int:
        """Walk the four buckets, whose names are the EducationType values."""
        if education is None:
            return 0

        written = 0
        for education_type in EducationType:
            entries: list[schemas.Education] = getattr(
                education, education_type.value
            )
            for entry in entries:
                session.execute(
                    insert(Education).values(
                        **self._mapper.education(
                            resume_id=resume_id,
                            entry=entry,
                            education_type=education_type,
                        )
                    )
                )
                written += 1

        return written
