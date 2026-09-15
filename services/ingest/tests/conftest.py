import os
from collections.abc import Iterator
from functools import cache
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

# Tracing talks to the X-Ray daemon, which no test has.
os.environ["POWERTOOLS_TRACE_DISABLED"] = "true"
os.environ["POWERTOOLS_SERVICE_NAME"] = "ingest"

os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "55432"
os.environ["DB_NAME"] = "test-name"
os.environ["DB_USER"] = "test-user"
os.environ["DB_PASSWORD"] = "test-password"
os.environ["DB_SSLMODE"] = "disable"

from aws_lambda_powertools import Logger
from sqlalchemy.orm import sessionmaker

from config import settings
from css_models import Base
from db import engine, url
from loader import CardWriter, Loader, ResumeMapper

TEST_DATABASE = "candidate_search_service_ingest_test"


def _connect_args() -> dict[str, Any]:
    """Wait three seconds, not the default fifteen, for a dead port."""
    return {
        "sslmode": settings.DB_SSLMODE,
        "connect_timeout": 3,
    }


@cache
def _unavailable() -> str | None:
    """Ask once whether Postgres is there, not once per test."""
    try:
        probe = create_engine(url(), connect_args=_connect_args())
        with probe.connect():
            pass
        probe.dispose()
    except OperationalError as error:
        return str(error).splitlines()[0]

    return None


@pytest.fixture(scope="session")
def database() -> Iterator[None]:
    """Recreate an empty database, point the environment at it, drop it."""
    reason = _unavailable()
    if reason is not None:
        # On CI the database is a service container, so absence is a failure.
        skip_or_fail = pytest.fail if os.environ.get("CI") else pytest.skip
        skip_or_fail(f"no Postgres to test against: {reason}")

    drop = text(f'DROP DATABASE IF EXISTS "{TEST_DATABASE}" WITH (FORCE)')
    create = text(f'CREATE DATABASE "{TEST_DATABASE}"')

    admin = create_engine(
        url(),
        connect_args=_connect_args(),
        isolation_level="AUTOCOMMIT",
    )
    with admin.connect() as connection:
        connection.execute(drop)
        connection.execute(create)

    previous = settings.DB_NAME
    settings.DB_NAME = TEST_DATABASE
    try:
        yield
    finally:
        settings.DB_NAME = previous
        with admin.connect() as connection:
            connection.execute(drop)
        admin.dispose()


@pytest.fixture(scope="session")
def schema(database: None) -> Iterator[Engine]:
    """Build the tables straight from the models the layer ships."""
    created = engine()
    Base.metadata.create_all(bind=created)
    try:
        yield created
    finally:
        created.dispose()


@pytest.fixture
def session(schema: Engine) -> Iterator[Session]:
    """Give each test a savepoint that is rolled back when it finishes."""
    with schema.connect() as connection:
        transaction = connection.begin()
        with Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
        ) as opened:
            yield opened
        transaction.rollback()


@pytest.fixture
def loader(session: Session) -> Loader:
    """A loader whose own transaction lands inside the test savepoint."""
    mapper = ResumeMapper()

    return Loader(
        session_factory=sessionmaker(
            bind=session.connection(),
            join_transaction_mode="create_savepoint",
        ),
        cards=CardWriter(mapper=mapper),
        mapper=mapper,
        logger=Logger(service="tests"),
    )
