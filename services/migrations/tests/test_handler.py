from pathlib import Path
from typing import Any

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

import handler
from handler import _config

HEAD = ScriptDirectory.from_config(_config()).get_current_head()
ARN = "arn:aws:lambda:us-east-1:440427555138:function:migrations"


class Context:
    """The parts of the Lambda context Powertools puts in every log line."""

    function_name = "candidate-search-service-database-migrations"
    memory_limit_in_mb = 512
    invoked_function_arn = ARN
    aws_request_id = "3f2a1b0c"

    def get_remaining_time_in_millis(self) -> int:
        return 300_000


class Recorder:
    """Stands in for alembic.command so no database is needed."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def upgrade(self, config: Config, revision: str) -> None:
        self.calls.append(("upgrade", revision))

    def downgrade(self, config: Config, revision: str) -> None:
        self.calls.append(("downgrade", revision))


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> Recorder:
    recorded = Recorder()
    monkeypatch.setattr(handler, "command", recorded)
    return recorded


def test_an_empty_payload_upgrades_to_head(recorder: Recorder) -> None:
    """A deploy invokes the Lambda with no payload at all."""
    answer = handler.handler(event={}, context=Context())

    assert recorder.calls == [("upgrade", "head")]
    assert answer == {"action": "upgrade", "revision": "head"}


def test_a_revision_can_be_pinned(recorder: Recorder) -> None:
    """Pinning is how a release is put on a known schema."""
    event: dict[str, Any] = {"action": "upgrade", "revision": HEAD}

    answer = handler.handler(event=event, context=Context())

    assert recorder.calls == [("upgrade", HEAD)]
    assert answer["revision"] == HEAD


def test_downgrade_steps_back_one_revision(recorder: Recorder) -> None:
    """Rolling back one step is the default because it is the safe one."""
    answer = handler.handler(event={"action": "downgrade"}, context=Context())

    assert recorder.calls == [("downgrade", "-1")]
    assert answer == {"action": "downgrade", "revision": "-1"}


def test_an_unknown_action_is_refused(recorder: Recorder) -> None:
    """A typo in the payload must fail loudly, not quietly upgrade."""
    with pytest.raises(ValueError, match="Unknown action: migrate"):
        handler.handler(event={"action": "migrate"}, context=Context())

    assert recorder.calls == []


def test_the_config_points_inside_the_package() -> None:
    """The Lambda has no working directory, so the paths must be absolute."""
    config = _config()
    location = config.get_main_option("script_location")

    assert config.config_file_name is not None
    assert location is not None
    assert Path(config.config_file_name).is_absolute()
    assert Path(location).is_absolute()


def test_the_files_alembic_needs_are_shipped() -> None:
    """Excluding the wrong path from the asset would only fail on AWS."""
    config = _config()
    location = config.get_main_option("script_location")

    assert location is not None
    assert Path(config.config_file_name or "").is_file()
    assert (Path(location) / "env.py").is_file()
    assert list((Path(location) / "versions").glob("*.py"))
