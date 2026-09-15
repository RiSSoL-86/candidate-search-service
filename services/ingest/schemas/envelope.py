import uuid

from schemas.base import Payload
from schemas.resume import Resume
from schemas.source import Source


class Envelope(Payload):
    """One queued message: a resume plus where it came from."""

    source: Source
    resume: Resume


class Result(Payload):
    """What the loader answers: the row id and whether it was new."""

    resume_id: uuid.UUID
    created: bool
