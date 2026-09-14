from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config

HERE = Path(__file__).parent


def _config() -> Config:
    """Point Alembic at the files shipped inside the Lambda package."""
    config = Config(file_=str(HERE / "alembic.ini"))
    config.set_main_option(
        name="script_location",
        value=str(HERE / "alembic"),
    )
    return config


def handler(event: dict[str, Any], context: Any) -> dict[str, str]:
    """Upgrade to head, or run the action and revision from the payload."""
    action = event.get("action", "upgrade")
    config = _config()

    if action == "upgrade":
        revision = event.get("revision", "head")
        command.upgrade(config=config, revision=revision)
    elif action == "downgrade":
        revision = event.get("revision", "-1")
        command.downgrade(config=config, revision=revision)
    else:
        raise ValueError(f"Unknown action: {action}")

    return {"action": action, "revision": revision}
