from schemas.base import Payload


class Area(Payload):
    """`area` on a resume and on an experience entry."""

    id: str
    name: str
    url: str | None = None
