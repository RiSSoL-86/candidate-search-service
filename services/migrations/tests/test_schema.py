import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from models import (
    Education,
    Employer,
    Experience,
    Metro,
    Owner,
    Resume,
)
from models.enums import DriverLicenseType, EducationType, Gender, ResumeType

DOWNLOADED = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)


def _owner(session: Session, hh_owner_id: str = "1") -> Owner:
    owner = Owner(hh_owner_id=hh_owner_id, first_name="Иван")
    session.add(owner)
    session.flush()
    return owner


def _resume(session: Session, owner: Owner, key: str = "a.json") -> Resume:
    resume = Resume(
        owner=owner,
        resume_type=ResumeType.FULL,
        downloaded_at=DOWNLOADED,
        s3_bucket="candidate-search-service",
        s3_key=f"resumes/{key}",
        s3_version_id=None,
        hh_resume_id="r1",
    )
    session.add(resume)
    session.flush()
    return resume


def test_a_resume_round_trips(session: Session) -> None:
    """The plain path works before any of the edge cases are worth asking."""
    owner = _owner(session)
    resume = _resume(session, owner)
    resume.salary_amount = Decimal("250000.00")
    resume.salary_currency = "RUR"
    resume.skill_set = ["Python", "SQL"]
    resume.photo = {"small": "https://hh.ru/a.png"}
    session.flush()
    session.expire_all()

    stored = session.get(Resume, resume.id)

    assert stored is not None
    assert stored.salary_amount == Decimal("250000.00")
    assert stored.skill_set == ["Python", "SQL"]
    assert stored.photo == {"small": "https://hh.ru/a.png"}
    assert stored.owner.hh_owner_id == "1"


def test_the_same_s3_object_cannot_arrive_twice(session: Session) -> None:
    """S3 retries its notification, and a retry must not double the row."""
    owner = _owner(session)
    _resume(session, owner)

    with pytest.raises(IntegrityError):
        _resume(session, owner)


def test_two_versions_of_one_object_are_separate(session: Session) -> None:
    """The bucket is versioned, so a re-upload is a genuinely new download."""
    owner = _owner(session)
    first = _resume(session, owner)
    first.s3_version_id = "v1"
    second = _resume(session, owner)
    second.s3_version_id = "v2"
    session.flush()

    assert first.id != second.id


def test_an_unknown_resume_type_is_refused(session: Session) -> None:
    """The CHECK is what keeps a typo out of the column."""
    owner = _owner(session)
    insert = text("""
        INSERT INTO resume (
            id, owner_id, resume_type, downloaded_at,
            s3_bucket, s3_key, hh_resume_id
        )
        VALUES (
            gen_random_uuid(), :owner, 'draft', :downloaded,
            'bucket', 'resumes/x.json', 'r9'
        )
    """)

    with pytest.raises(DBAPIError) as failure:
        session.execute(insert, {"owner": owner.id, "downloaded": DOWNLOADED})

    assert "ck_resume_resume_type" in str(failure.value)


def test_a_known_resume_type_is_accepted(session: Session) -> None:
    """The same insert passes once the value is one HH actually sends."""
    owner = _owner(session)
    session.add(
        Resume(
            owner=owner,
            resume_type=ResumeType.SHORT,
            downloaded_at=DOWNLOADED,
            s3_bucket="bucket",
            s3_key="resumes/x.json",
            hh_resume_id="r9",
        )
    )
    session.flush()

    kinds = session.scalars(select(Resume.resume_type)).all()

    assert list(kinds) == [ResumeType.SHORT]


def test_the_enum_value_is_stored_not_the_member_name(
    session: Session,
) -> None:
    """A raw SQL search has to match 'full', not 'FULL'."""
    owner = _owner(session)
    _resume(session, owner)

    raw = session.execute(text("SELECT resume_type FROM resume")).scalar_one()

    assert raw == "full"


def test_deleting_a_resume_takes_its_children(session: Session) -> None:
    """A download and its parsed rows are one unit of data."""
    owner = _owner(session)
    resume = _resume(session, owner)
    employer = Employer(name="Konsol", hh_employer_id="777")
    session.add(employer)
    session.add(
        Experience(resume=resume, employer=employer, position="Developer")
    )
    session.add(Education(resume=resume, education_type=EducationType.PRIMARY))
    session.flush()

    session.execute(
        text("DELETE FROM resume WHERE id = :id"), {"id": resume.id}
    )

    assert session.scalar(select(func.count()).select_from(Experience)) == 0
    assert session.scalar(select(func.count()).select_from(Education)) == 0
    assert session.scalar(select(func.count()).select_from(Employer)) == 1


def test_an_owner_with_resumes_cannot_be_deleted(session: Session) -> None:
    """Without this the resume rows would point at a person who is gone."""
    owner = _owner(session)
    _resume(session, owner)

    with pytest.raises(IntegrityError):
        session.execute(
            text("DELETE FROM owner WHERE id = :id"), {"id": owner.id}
        )


def test_an_owner_is_stored_once(session: Session) -> None:
    """One person, one card, however many resumes they have."""
    _owner(session, hh_owner_id="42")

    with pytest.raises(IntegrityError):
        _owner(session, hh_owner_id="42")


def test_an_employer_is_stored_once(session: Session) -> None:
    """The same company must not fan out into a card per resume."""
    session.add(Employer(name="Konsol", hh_employer_id="777"))
    session.flush()
    session.add(Employer(name="Konsol Ltd", hh_employer_id="777"))

    with pytest.raises(IntegrityError):
        session.flush()


def test_generated_keys_are_uuid_version_7(session: Session) -> None:
    """Version 7 keys carry their time, so they insert without page splits."""
    owner = _owner(session)
    first = _resume(session, owner, key="a.json")
    second = _resume(session, owner, key="b.json")

    assert first.id.version == 7
    assert second.id.version == 7
    assert first.id < second.id


def test_a_missing_json_value_is_a_sql_null(session: Session) -> None:
    """A JSON 'null' would break IS NULL and every jsonb function."""
    owner = _owner(session)
    resume = _resume(session, owner)
    resume.photo = None
    session.flush()

    query = text("""
        SELECT photo IS NULL, photo::text
        FROM resume WHERE id = :id
    """)
    is_null, rendered = session.execute(query, {"id": resume.id}).one()

    assert is_null is True
    assert rendered is None


def test_json_arrays_can_be_searched(session: Session) -> None:
    """Unpacking a JSONB array is how the search over these columns works."""
    owner = _owner(session)
    resume = _resume(session, owner)
    resume.professional_roles = [{"id": "96", "name": "Программист"}]
    session.flush()

    query = text("""
        SELECT role ->> 'name'
        FROM resume, jsonb_array_elements(professional_roles) AS role
        WHERE resume.id = :id
    """)

    assert session.execute(query, {"id": resume.id}).scalar_one() == (
        "Программист"
    )


def test_timestamps_keep_their_time_zone(session: Session) -> None:
    """A naive timestamp would silently shift the download time."""
    owner = _owner(session)
    resume = _resume(session, owner)
    session.expire_all()
    stored = session.get(Resume, resume.id)

    assert stored is not None
    assert stored.downloaded_at.tzinfo is not None
    assert stored.downloaded_at == DOWNLOADED
    assert stored.created_at.tzinfo is not None


def test_updated_at_moves_on_its_own(schema: Engine) -> None:
    """Knowing when a row last changed must not depend on the caller."""
    with Session(schema) as opened:
        owner = _owner(opened, hh_owner_id="stamp")
        opened.commit()
        before = owner.updated_at

        owner.first_name = "Пётр"
        opened.commit()
        after = owner.updated_at

        opened.execute(
            text("DELETE FROM owner WHERE id = :id"), {"id": owner.id}
        )
        opened.commit()

    assert after > before


def test_updated_at_holds_still_inside_one_transaction(
    session: Session,
) -> None:
    """now() is the transaction clock: one batch, one timestamp."""
    owner = _owner(session)
    stamped = owner.updated_at

    owner.first_name = "Пётр"
    session.flush()

    assert owner.updated_at == stamped
    assert owner.created_at == stamped


def test_driver_licences_are_a_searchable_array(session: Session) -> None:
    """Storing them as an array is what lets a query ask for one licence."""
    owner = _owner(session)
    resume = _resume(session, owner)
    resume.driver_license_types = [
        DriverLicenseType.B,
        DriverLicenseType.C,
    ]
    session.flush()

    query = text("""
        SELECT count(*) FROM resume
        WHERE driver_license_types @> ARRAY['B']::varchar[]
    """)

    assert session.execute(query).scalar_one() == 1

    session.expire_all()
    stored = session.get(Resume, resume.id)

    assert stored is not None
    assert stored.driver_license_types == [
        DriverLicenseType.B,
        DriverLicenseType.C,
    ]


def test_the_owner_card_holds_the_person(session: Session) -> None:
    """Personal data belongs to the person, not to a single download."""
    owner = Owner(
        hh_owner_id="55",
        first_name="Иван",
        last_name="Петров",
        age=33,
        gender=Gender.MALE,
        birth_date=date(1993, 5, 1),
        contact=[{"type": {"id": "email"}, "value": "i@example.com"}],
    )
    session.add(owner)
    session.flush()
    session.expire_all()

    stored = session.get(Owner, owner.id)

    assert stored is not None
    assert stored.gender is Gender.MALE
    assert stored.birth_date == date(1993, 5, 1)
    assert stored.contact is not None
    assert stored.contact[0]["value"] == "i@example.com"


def test_a_metro_station_is_shared_between_resumes(session: Session) -> None:
    """Lookups stay single rows so a search can group by them."""
    metro = Metro(hh_metro_id="1.1", name="Тверская")
    session.add(metro)
    owner = _owner(session)
    first = _resume(session, owner, key="a.json")
    second = _resume(session, owner, key="b.json")
    first.metro = metro
    second.metro = metro
    session.flush()

    assert session.scalar(select(func.count()).select_from(Metro)) == 1


def test_the_target_search_runs_on_plain_sql(session: Session) -> None:
    """Find people who worked somewhere for at least a year."""
    owner = _owner(session)
    resume = _resume(session, owner)
    employer = Employer(name="Konsol", hh_employer_id="777")
    session.add(employer)
    session.add(
        Experience(
            resume=resume,
            employer=employer,
            company="Konsol",
            position="Developer",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 6, 1),
        )
    )
    session.flush()

    query = text("""
        SELECT owner.hh_owner_id
        FROM experience
        JOIN resume ON resume.id = experience.resume_id
        JOIN owner ON owner.id = resume.owner_id
        JOIN employer ON employer.id = experience.employer_id
        WHERE employer.name = 'Konsol'
          AND age(
              coalesce(experience.end_date, current_date),
              experience.start_date
          ) >= interval '1 year'
    """)

    assert session.execute(query).scalar_one() == "1"


def test_an_id_is_never_reused_across_tables(session: Session) -> None:
    """Keys are generated, not taken from HH, so they cannot collide."""
    owner = _owner(session)
    resume = _resume(session, owner)

    assert isinstance(owner.id, uuid.UUID)
    assert owner.id != resume.id
