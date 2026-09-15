from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from css_models import (
    Area,
    Education,
    Employer,
    Experience,
    Metro,
    Owner,
    Resume,
)
from css_models.enums import DriverLicenseType, EducationType, Gender
from loader import Loader
from schemas import Envelope
from tests.payloads import envelope


def _count(
    session: Session, model: Any, column: Any, value: Any
) -> int | None:
    """Count only our own rows: the handler tests commit into this database."""
    return session.scalar(
        select(func.count()).select_from(model).where(column == value)
    )


def _load(loader: Loader, session: Session, **overrides: Any) -> Resume:
    """Run the loader over the sample payload and hand back the row."""
    result = loader.execute(
        envelope=Envelope.model_validate(envelope(**overrides))
    )
    return session.get_one(Resume, result.resume_id)


def test_the_payload_lands_in_the_resume_columns(
    loader: Loader, session: Session
) -> None:
    """This is the whole point: JSON in, one queryable row out."""
    resume = _load(loader, session)

    assert resume.hh_resume_id == "002b134f0010fee16600261bcc424743354b70"
    assert resume.title == "Финансовый аналитик"
    assert resume.salary_amount == Decimal("350000")
    assert resume.salary_currency == "RUR"
    assert resume.total_experience_months == 22
    assert resume.platform_id == "headhunter"
    assert resume.skill_set == ["SQL", "Python"]


def test_the_provenance_is_written_with_the_row(
    loader: Loader, session: Session
) -> None:
    """Without it we could never tell which S3 object produced the row."""
    resume = _load(loader, session)

    assert resume.s3_bucket == "candidate-search-service-resumes"
    assert resume.s3_key == "full_resumes_hh/002b134f.json"
    assert resume.s3_version_id == "5jK3xQ"


def test_the_json_blocks_are_stored_whole(
    loader: Loader, session: Session
) -> None:
    """Fields with no business meaning yet still have to survive the trip."""
    resume = _load(loader, session)

    assert resume.education_level == {"id": "bachelor", "name": "Бакалавр"}
    assert resume.relocation_type == {"id": "no_relocation"}
    assert resume.schedules == [{"id": "remote", "name": "Удалённая работа"}]
    assert resume.photo == {"small": "https://img.hhcdn.ru/photo/1.jpeg"}


def test_the_person_goes_to_the_owner_table(
    loader: Loader, session: Session
) -> None:
    """The owner is the only handle that survives across downloads."""
    resume = _load(loader, session)

    assert resume.owner.hh_owner_id == "171538711"
    assert resume.owner.age == 22
    assert resume.owner.gender is Gender.MALE


def test_the_jobs_land_as_rows_of_their_own(
    loader: Loader, session: Session
) -> None:
    """A searcher has to filter on one company, not on a JSON blob."""
    resume = _load(loader, session)
    jobs = sorted(
        resume.experiences, key=lambda job: job.hh_experience_id or ""
    )

    assert len(jobs) == 2
    assert jobs[0].company == "Lod Capital"
    assert jobs[0].employer_id is None
    assert jobs[1].position == "Аналитик"
    assert jobs[1].employer is not None
    assert jobs[1].employer.name == "Ростелеком"
    assert jobs[1].area is not None
    assert jobs[1].area.name == "Казань"


def test_the_four_education_buckets_are_flattened(
    loader: Loader, session: Session
) -> None:
    """HH splits study entries by kind and the column keeps that kind."""
    resume = _load(loader, session)
    kinds = {entry.education_type for entry in resume.educations}

    assert len(resume.educations) == 2
    assert kinds == {EducationType.PRIMARY, EducationType.ADDITIONAL}


def test_the_same_object_twice_is_a_no_op(
    loader: Loader, session: Session
) -> None:
    """SQS delivers at least once, so a replay has to be harmless."""
    first = loader.execute(envelope=Envelope.model_validate(envelope()))
    second = loader.execute(envelope=Envelope.model_validate(envelope()))

    key = "full_resumes_hh/002b134f.json"

    assert first.created is True
    assert second.created is False
    assert second.resume_id == first.resume_id
    assert _count(session, Resume, Resume.s3_key, key) == 1
    assert (
        _count(session, Experience, Experience.resume_id, first.resume_id) == 2
    )


def test_a_new_version_of_the_same_key_is_a_new_row(
    loader: Loader, session: Session
) -> None:
    """Every download is history, so nothing is ever overwritten."""
    first = _load(loader, session, version_id="5jK3xQ")
    second = _load(loader, session, version_id="9pL0zR")

    assert first.id != second.id
    assert first.owner_id == second.owner_id
    assert _count(session, Resume, Resume.s3_key, first.s3_key) == 2


def test_the_shared_cards_are_written_once(
    loader: Loader, session: Session
) -> None:
    """Two downloads of one person must not double the geography rows."""
    _load(loader, session, key="a.json")
    _load(loader, session, key="b.json")

    assert _count(session, Owner, Owner.hh_owner_id, "171538711") == 1
    assert _count(session, Metro, Metro.hh_metro_id, "14.195") == 1
    assert _count(session, Employer, Employer.hh_employer_id, "5390761") == 1
    # Москва from the resume and Казань from the second job.
    assert _count(session, Area, Area.hh_area_id, "1") == 1
    assert _count(session, Area, Area.hh_area_id, "88") == 1


def test_a_driver_licence_we_do_not_know_is_dropped(
    loader: Loader, session: Session
) -> None:
    """A value HH invents later must not fail the whole load."""
    resume = _load(
        loader, session, driver_license_types=[{"id": "B"}, {"id": "Z"}]
    )

    assert resume.driver_license_types == [DriverLicenseType.B]


def test_a_short_resume_loads_with_almost_nothing(
    loader: Loader, session: Session
) -> None:
    """Half the fields are missing and the row still has to be written."""
    result = loader.execute(
        envelope=Envelope.model_validate(
            {
                "source": {
                    "bucket": "candidate-search-service-resumes",
                    "key": "short_resumes_hh/1.json",
                    "downloaded_at": "2026-09-14T12:00:00+00:00",
                    "resume_type": "short",
                },
                "resume": {"id": "abc", "owner": {"id": "42"}},
            }
        )
    )
    resume = session.get_one(Resume, result.resume_id)

    assert resume.title is None
    assert resume.area_id is None
    assert resume.experiences == []
    assert (
        _count(session, Education, Education.resume_id, result.resume_id) == 0
    )
