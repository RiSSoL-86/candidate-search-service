from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.batch import (
    BatchProcessor,
    EventType,
    process_partial_response,
)
from aws_lambda_powertools.utilities.batch.types import (
    PartialItemFailureResponse,
)
from aws_lambda_powertools.utilities.data_classes.sqs_event import SQSRecord
from aws_lambda_powertools.utilities.typing import LambdaContext
from sqlalchemy.orm import sessionmaker

from config import settings
from db import engine
from loader import CardWriter, Loader, ResumeMapper
from schemas import Envelope

logger = Logger(log_uncaught_exceptions=True, level=settings.LOG_LEVEL)
tracer = Tracer()
metrics = Metrics(namespace=settings.METRICS_NAMESPACE)

mapper = ResumeMapper()
loader = Loader(
    session_factory=sessionmaker(bind=engine()),
    cards=CardWriter(mapper=mapper),
    mapper=mapper,
    logger=logger,
)

processor = BatchProcessor(event_type=EventType.SQS)


@tracer.capture_method
def record_handler(record: SQSRecord) -> dict[str, Any]:
    """Load one queued resume; raising here fails this message alone."""
    logger.info(
        "Message received",
        message_id=record.message_id,
        queue=record.event_source_arn,
        receive_count=record.attributes.approximate_receive_count,
        sent_at=record.attributes.sent_timestamp,
        body=record.json_body,
    )

    envelope = Envelope.model_validate(record.json_body)
    logger.info(
        "Message parsed",
        message_id=record.message_id,
        s3_bucket=envelope.source.bucket,
        s3_key=envelope.source.key,
        s3_version_id=envelope.source.version_id,
        resume_type=envelope.source.resume_type,
        hh_resume_id=envelope.resume.id,
        hh_owner_id=envelope.resume.owner.id,
    )

    result = loader.execute(envelope=envelope)
    logger.info(
        "Message handled",
        message_id=record.message_id,
        resume_id=str(result.resume_id),
        resume_created=result.created,
    )

    metrics.add_metric(
        name="ResumesLoaded" if result.created else "ResumesSkipped",
        unit=MetricUnit.Count,
        value=1,
    )
    return result.model_dump(mode="json")


@metrics.log_metrics(capture_cold_start_metric=True)
@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(
    event: dict[str, Any], context: LambdaContext
) -> PartialItemFailureResponse:
    """Take one SQS batch and report only the messages that failed."""
    logger.info("Batch received", messages=len(event.get("Records", [])))

    response = process_partial_response(
        event=event,
        record_handler=record_handler,
        processor=processor,
        context=context,
    )

    failures = response["batchItemFailures"]
    logger.info("Batch handled", failed=len(failures), failures=failures)
    return response
