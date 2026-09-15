from enum import StrEnum

from css_models.enums import DriverLicenseType
from schemas import Ident


def enum_member[T: StrEnum](enum: type[T], value: str | None) -> T | None:
    """Drop a value HH invented after our CHECK constraint was written."""
    if value is None:
        return None

    try:
        return enum(value)
    except ValueError:
        return None


def driver_licenses(types: list[Ident] | None) -> list[DriverLicenseType]:
    """Flatten `[{"id": "B"}]` into the array column the resume table has."""
    if types is None:
        return []

    known = (enum_member(DriverLicenseType, item.id) for item in types)
    return [license for license in known if license is not None]
