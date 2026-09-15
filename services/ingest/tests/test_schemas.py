from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from css_models.enums import ResumeType
from schemas import Envelope
from tests.payloads import envelope


def test_the_envelope_carries_the_source_and_the_resume() -> None:
    """Provenance is the caller's job; the Lambda only records it."""
    parsed = Envelope.model_validate(envelope())

    assert parsed.source.bucket == "candidate-search-service-resumes"
    assert parsed.source.version_id == "5jK3xQ"
    assert parsed.source.resume_type is ResumeType.FULL
    assert parsed.source.downloaded_at == datetime(2026, 9, 14, 12, tzinfo=UTC)


def test_an_unversioned_bucket_is_allowed() -> None:
    """A bucket without versioning hands back no VersionId at all."""
    parsed = Envelope.model_validate(envelope(version_id=None))

    assert parsed.source.version_id is None


def test_keys_we_have_no_column_for_are_dropped() -> None:
    """HH keeps adding fields and none of them may reach an INSERT."""
    parsed = Envelope.model_validate(envelope(favorited=True, marked=False))

    assert not hasattr(parsed.resume, "favorited")


def test_the_numbers_and_dates_are_parsed_not_passed_through() -> None:
    """The columns are numeric and date, so the strings have to be typed."""
    parsed = Envelope.model_validate(envelope())

    assert parsed.resume.salary is not None
    assert parsed.resume.salary.amount == Decimal("350000")
    assert parsed.resume.birth_date == date(2003, 9, 9)
    assert parsed.resume.experience[1].end == date(2024, 10, 1)


def test_a_short_resume_needs_only_an_id_and_an_owner() -> None:
    """Short payloads carry a fraction of the fields and must still load."""
    parsed = Envelope.model_validate(
        {
            "source": {
                "bucket": "b",
                "key": "short_resumes_hh/1.json",
                "downloaded_at": "2026-09-14T12:00:00+00:00",
                "resume_type": "short",
            },
            "resume": {"id": "abc", "owner": {"id": "42"}},
        }
    )

    assert parsed.resume.experience == []
    assert parsed.resume.education is None


def test_a_resume_without_an_owner_is_refused() -> None:
    """Without owner.id there is no way to tie downloads to one person."""
    payload = envelope()
    del payload["resume"]["owner"]

    with pytest.raises(ValidationError, match="owner"):
        Envelope.model_validate(payload)


def test_an_unknown_resume_type_is_refused() -> None:
    """The column is a CHECK constraint, so a typo has to fail early."""
    payload = envelope()
    payload["source"]["resume_type"] = "medium"

    with pytest.raises(ValidationError, match="resume_type"):
        Envelope.model_validate(payload)
