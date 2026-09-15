import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

import handler as handler_module
from css_models import Resume
from handler import handler
from loader import CardWriter, Loader, ResumeMapper
from tests.payloads import Context, envelope, sqs_event


@pytest.fixture
def aws(schema: Engine, monkeypatch: pytest.MonkeyPatch) -> Engine:
    """Point the loader the Lambda built on import at the test database."""
    mapper = ResumeMapper()
    monkeypatch.setattr(
        handler_module,
        "loader",
        Loader(
            session_factory=sessionmaker(bind=schema),
            cards=CardWriter(mapper=mapper),
            mapper=mapper,
            logger=handler_module.logger,
        ),
    )
    return schema


def _rows(engine: Engine, key: str) -> int | None:
    """Count the snapshots written for one S3 key."""
    with Session(engine) as session:
        return session.scalar(
            select(func.count())
            .select_from(Resume)
            .where(Resume.s3_key == key)
        )


def test_the_resume_is_committed(aws: Engine) -> None:
    """A Lambda that rolls back on return would write nothing at all."""
    answer = handler(
        event=sqs_event(envelope(key="committed.json")),
        context=Context(),
    )

    assert answer == {"batchItemFailures": []}
    assert _rows(aws, "committed.json") == 1


def test_a_replay_of_the_batch_writes_nothing_twice(aws: Engine) -> None:
    """SQS delivers at least once, so the same batch can arrive again."""
    batch = sqs_event(envelope(key="replayed.json"))

    handler(event=batch, context=Context())
    answer = handler(event=batch, context=Context())

    assert answer == {"batchItemFailures": []}
    assert _rows(aws, "replayed.json") == 1


def test_only_the_broken_message_is_sent_back(aws: Engine) -> None:
    """The point of the batch response: one bad JSON must not block nine."""
    answer = handler(
        event=sqs_event(
            {"source": envelope()["source"]},
            envelope(key="neighbour.json"),
        ),
        context=Context(),
    )

    assert answer == {"batchItemFailures": [{"itemIdentifier": "message-0"}]}
    assert _rows(aws, "neighbour.json") == 1
