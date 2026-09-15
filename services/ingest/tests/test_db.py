from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event

import db
from config import Settings, settings


class Client:
    """Stands in for the RDS client so nothing is asked of the network."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def generate_db_auth_token(self, **kwargs: Any) -> str:
        self.calls.append(kwargs)
        return "iam-token"


@pytest.fixture
def aws(monkeypatch: pytest.MonkeyPatch) -> Client:
    """The settings as the Lambda sees them, with the RDS client faked out."""
    monkeypatch.setattr(settings, "DB_PASSWORD", None)
    monkeypatch.setattr(settings, "DB_SSLMODE", "require")

    client = Client()
    monkeypatch.setattr(db.boto3, "client", lambda name: client)
    return client


def test_the_url_is_built_for_psycopg(aws: Client) -> None:
    """The driver has to be spelled out or SQLAlchemy picks psycopg2."""
    built = db.url()

    assert built.drivername == "postgresql+psycopg"
    assert built.host == settings.DB_HOST
    assert built.port == settings.DB_PORT
    assert built.database == settings.DB_NAME
    assert built.username == settings.DB_USER


def test_an_iam_token_is_minted_when_there_is_no_password(
    aws: Client,
) -> None:
    """This is the normal path: the Lambda never holds a real password."""
    built = db.url()

    assert built.password == "iam-token"
    assert aws.calls == [
        {
            "DBHostname": settings.DB_HOST,
            "Port": settings.DB_PORT,
            "DBUsername": settings.DB_USER,
        }
    ]


def test_a_password_short_circuits_the_token(
    aws: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DB_PASSWORD is the bootstrap path and the local docker path."""
    monkeypatch.setattr(settings, "DB_PASSWORD", "secret")

    built = db.url()

    assert built.password == "secret"
    assert aws.calls == []


def test_the_password_is_not_printed(
    aws: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The URL ends up in Alembic logs, which end up in CloudWatch."""
    monkeypatch.setattr(settings, "DB_PASSWORD", "secret")

    built = db.url()

    assert built.password == "secret"
    assert ":secret@" not in str(built)
    assert ":***@" in str(built)
    assert ":***@" in built.render_as_string()


def test_a_missing_setting_is_caught_on_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Better a named error on cold start than a wrong database at runtime."""
    monkeypatch.delenv("DB_HOST")

    with pytest.raises(ValidationError, match="DB_HOST"):
        Settings()


def test_the_port_is_a_number(monkeypatch: pytest.MonkeyPatch) -> None:
    """CDK hands the port over as a string token, psycopg wants an int."""
    monkeypatch.setenv("DB_PORT", "5432")

    assert Settings().DB_PORT == 5432


def test_the_lambda_needs_no_password_and_no_sslmode() -> None:
    """CDK sets neither, so the defaults are what actually runs in AWS."""
    fields = Settings.model_fields

    assert fields["DB_PASSWORD"].default is None
    assert fields["DB_SSLMODE"].default == "require"


def _capture(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Keep the engine real, since it carries the listeners we check."""
    captured: dict[str, Any] = {}

    def spy(url: Any, **kwargs: Any) -> Any:
        captured.update(kwargs)
        return create_engine(url, **kwargs)

    monkeypatch.setattr(db, "create_engine", spy)
    return captured


def test_the_connection_requires_tls_by_default(
    aws: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RDS rejects an IAM token over a plaintext connection."""
    captured = _capture(monkeypatch)

    db.engine()

    assert captured["connect_args"] == {"sslmode": "require"}


def test_tls_can_be_relaxed_for_local_docker(
    aws: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The throwaway container has no certificate to offer."""
    captured = _capture(monkeypatch)
    monkeypatch.setattr(settings, "DB_SSLMODE", "disable")

    db.engine()

    assert captured["connect_args"] == {"sslmode": "disable"}


def test_every_connection_is_opened_with_a_fresh_token(aws: Client) -> None:
    """A warm Lambda outlives the fifteen minutes a token is good for."""
    created = db.engine()
    params: dict[str, Any] = {}

    db.refresh_password(None, None, (), params)

    assert event.contains(created, "do_connect", db.refresh_password)
    assert params["password"] == "iam-token"
