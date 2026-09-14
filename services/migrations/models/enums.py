from enum import StrEnum

from sqlalchemy import Enum


class ResumeType(StrEnum):
    """Which HH endpoint the resume snapshot came from."""

    SHORT = "short"
    FULL = "full"


class Gender(StrEnum):
    """Raw `gender.id` values HH returns."""

    MALE = "male"
    FEMALE = "female"


class EducationType(StrEnum):
    """Which `education` bucket the entry was listed under."""

    PRIMARY = "primary"
    ADDITIONAL = "additional"
    ATTESTATION = "attestation"
    ELEMENTARY = "elementary"


class DriverLicenseType(StrEnum):
    """Raw `driver_license_types[].id` values HH returns."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    BE = "BE"
    CE = "CE"
    DE = "DE"
    TM = "TM"
    TB = "TB"


def choice(enum: type[StrEnum], name: str, constraint: bool = True) -> Enum:
    """Store the member value in a VARCHAR, so a new option is a CHECK swap."""
    return Enum(
        enum,
        name=name,
        native_enum=False,
        create_constraint=constraint,
        values_callable=lambda members: [member.value for member in members],
    )
