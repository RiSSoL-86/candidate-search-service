from pydantic import BaseModel, ConfigDict


class Payload(BaseModel):
    """Base for every HH object: keys we have no column for are dropped."""

    model_config = ConfigDict(extra="ignore")


class Ident(Payload):
    """An HH dictionary value, of which only the id is worth a column."""

    id: str | None = None
