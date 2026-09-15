from schemas.base import Payload


class Owner(Payload):
    """`owner`, the only stable handle on the person behind the resumes."""

    id: str
