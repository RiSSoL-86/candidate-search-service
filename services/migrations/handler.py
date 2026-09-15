from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

from config import settings

HERE = Path(__file__).parent

logger = Logger(log_uncaught_exceptions=True, level=settings.LOG_LEVEL)
tracer = Tracer()
metrics = Metrics(namespace=settings.METRICS_NAMESPACE)


def _config() -> Config:
    """Point Alembic at the files shipped inside the Lambda package."""
    config = Config(file_=str(HERE / "alembic.ini"))
    config.set_main_option(
        name="script_location",
        value=str(HERE / "alembic"),
    )
    return config


@metrics.log_metrics(capture_cold_start_metric=True)
@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, str]:
    """Upgrade to head, or run the action and revision from the payload."""
    action = event.get("action", "upgrade")
    config = _config()
    logger.info(
        "Event received",
        event=event,
        action=action,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        script_location=config.get_main_option("script_location"),
    )

    if action == "upgrade":
        revision = event.get("revision", "head")
        logger.info("Upgrading", revision=revision)
        command.upgrade(config=config, revision=revision)
    elif action == "downgrade":
        revision = event.get("revision", "-1")
        logger.info("Downgrading", revision=revision)
        command.downgrade(config=config, revision=revision)
    else:
        raise ValueError(f"Unknown action: {action}")

    logger.info("Migrations run", action=action, revision=revision)
    metrics.add_metric(
        name="MigrationsUpgraded"
        if action == "upgrade"
        else "MigrationsDowngraded",
        unit=MetricUnit.Count,
        value=1,
    )
    return {"action": action, "revision": revision}
