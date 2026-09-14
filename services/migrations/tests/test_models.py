import uuid

import pytest
from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    DateTime,
    Enum,
    PrimaryKeyConstraint,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

import models
from models import Base

TABLES = list(Base.metadata.sorted_tables)
NAMES = [table.name for table in TABLES]

PREFIXES = ("pk_", "fk_", "uq_", "ck_", "ix_")

# fmt: off
# Words Postgres refuses as a bare identifier, so no column may use one.
RESERVED = {
    "all", "analyse", "analyze", "and", "any", "array", "as", "asc",
    "asymmetric", "both", "case", "cast", "check", "collate", "column",
    "constraint", "create", "current_catalog", "current_date",
    "current_role", "current_time", "current_timestamp", "current_user",
    "default", "deferrable", "desc", "distinct", "do", "else", "end",
    "except", "false", "fetch", "for", "foreign", "from", "grant", "group",
    "having", "in", "initially", "intersect", "into", "lateral", "leading",
    "limit", "localtime", "localtimestamp", "not", "null", "offset", "on",
    "only", "or", "order", "placing", "primary", "references", "returning",
    "select", "session_user", "some", "symmetric", "table", "then", "to",
    "trailing", "true", "union", "unique", "user", "using", "variadic",
    "when", "where", "window", "with",
}
# fmt: on


def _leading_columns(table: Table) -> set[str]:
    """Columns an index can be looked up by on its own."""
    covered = set()

    for index in table.indexes:
        name = getattr(next(iter(index.expressions)), "name", None)
        if name is not None:
            covered.add(str(name))

    for constraint in table.constraints:
        if isinstance(constraint, PrimaryKeyConstraint | UniqueConstraint):
            columns = list(constraint.columns)
            if columns:
                covered.add(columns[0].name)

    return covered


def _enum_types(table: Table) -> list[tuple[str, Enum, bool]]:
    """Enum columns as (column name, enum type, whether it is an array)."""
    found: list[tuple[str, Enum, bool]] = []

    for column in table.columns:
        kind = column.type
        if isinstance(kind, Enum):
            found.append((column.name, kind, False))
        elif isinstance(kind, ARRAY) and isinstance(kind.item_type, Enum):
            found.append((column.name, kind.item_type, True))

    return found


@pytest.mark.parametrize("table", TABLES, ids=NAMES)
def test_primary_key_is_a_generated_uuid(table: Table) -> None:
    """Every row is identified by a UUIDv7 the service generates."""
    key = list(table.primary_key.columns)

    assert [column.name for column in key] == ["id"]
    assert key[0].type.python_type is uuid.UUID
    assert key[0].default is not None
    # SQLAlchemy wraps a zero-argument default, so compare by name.
    generator = getattr(key[0].default, "arg", None)

    assert getattr(generator, "__name__", None) == "uuid7"


@pytest.mark.parametrize("table", TABLES, ids=NAMES)
def test_rows_carry_timestamps(table: Table) -> None:
    """The database stamps when a row appeared, not the caller."""
    for name in ("created_at", "updated_at"):
        column = table.columns[name]

        assert column.server_default is not None, name
        assert not column.nullable, name
        assert isinstance(column.type, DateTime), name
        assert column.type.timezone, f"{name} must keep the time zone"


@pytest.mark.parametrize("table", TABLES, ids=NAMES)
def test_foreign_keys_are_indexed(table: Table) -> None:
    """Postgres does not index a foreign key for you; joins would crawl."""
    covered = _leading_columns(table)

    for constraint in table.foreign_key_constraints:
        for column in constraint.columns:
            assert column.name in covered, (
                f"{table.name}.{column.name} points at another table "
                f"but no index starts with it"
            )


@pytest.mark.parametrize("table", TABLES, ids=NAMES)
def test_jsonb_columns_store_a_real_null(table: Table) -> None:
    """Without none_as_null a missing value becomes the JSON scalar null."""
    for column in table.columns:
        if isinstance(column.type, JSONB):
            assert column.type.none_as_null, column.name


@pytest.mark.parametrize("table", TABLES, ids=NAMES)
def test_enums_are_text_with_a_check(table: Table) -> None:
    """A new HH option must be a constraint swap, not a type migration."""
    for name, enum, is_array in _enum_types(table):
        assert not enum.native_enum, f"{name} would need ALTER TYPE"
        assert enum.enum_class is not None, f"{name} is not a Python enum"
        assert enum.enums == [member.value for member in enum.enum_class], (
            f"{name} must store the HH value, not the member name"
        )
        if not is_array:
            assert enum.create_constraint, f"{name} accepts anything"


@pytest.mark.parametrize("table", TABLES, ids=NAMES)
def test_constraint_names_follow_the_convention(table: Table) -> None:
    """A generated name cannot be dropped by a later migration."""
    for item in [*table.constraints, *table.indexes]:
        name = getattr(item, "name", None)

        assert isinstance(name, str) and name, f"unnamed on {table.name}"
        assert name.startswith(PREFIXES), name


@pytest.mark.parametrize("table", TABLES, ids=NAMES)
def test_no_identifier_is_a_reserved_word(table: Table) -> None:
    """A reserved word forces quoting in every hand-written query."""
    assert table.name.lower() not in RESERVED

    for column in table.columns:
        assert column.name.lower() not in RESERVED, column.name


@pytest.mark.parametrize("table", TABLES, ids=NAMES)
def test_checks_come_only_from_enums(table: Table) -> None:
    """Every CHECK is generated by an enum, none was bolted on by hand."""
    enums = {name for name, _, array in _enum_types(table) if not array}
    checks = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert checks == {f"ck_{table.name}_{name}" for name in enums}


@pytest.mark.parametrize("table", TABLES, ids=NAMES)
def test_indexes_are_not_duplicated(table: Table) -> None:
    """Two indexes over the same columns cost writes and buy nothing."""
    signatures = [
        tuple(str(expression) for expression in index.expressions)
        for index in table.indexes
    ]

    assert len(signatures) == len(set(signatures)), table.name


def test_every_model_is_exported() -> None:
    """A model missing from the package is invisible to autogenerate."""
    mapped = {mapper.class_.__name__ for mapper in Base.registry.mappers}

    assert set(models.__all__) == mapped | {"Base"}
    assert models.__all__ == sorted(models.__all__)


def test_children_are_deleted_with_their_resume() -> None:
    """Rows that belong to one download must not outlive it."""
    for name in ("experience", "education"):
        table = Base.metadata.tables[name]
        parents = [
            constraint
            for constraint in table.foreign_key_constraints
            if constraint.referred_table.name == "resume"
        ]

        assert parents, name
        for constraint in parents:
            assert constraint.ondelete == "CASCADE", name


def test_shared_cards_are_never_cascaded_away() -> None:
    """Lookups are reused across resumes, so they must not cascade."""
    for table in TABLES:
        for constraint in table.foreign_key_constraints:
            referred = constraint.referred_table.name
            if referred in ("area", "metro", "employer", "owner"):
                assert constraint.ondelete is None, (
                    f"{table.name} would delete rows from {referred}"
                )


def test_foreign_keys_point_at_a_primary_key() -> None:
    """A link to a non-key column would let duplicates break the join."""
    for table in TABLES:
        for constraint in table.foreign_key_constraints:
            for key in constraint.elements:
                assert key.column.primary_key, str(key.target_fullname)


def test_the_s3_pointer_cannot_be_stored_twice() -> None:
    """An S3 event is delivered at least once, so an object can repeat."""
    resume = Base.metadata.tables["resume"]
    unique = [
        constraint
        for constraint in resume.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert len(unique) == 1
    assert [column.name for column in unique[0].columns] == [
        "s3_bucket",
        "s3_key",
        "s3_version_id",
    ]
    assert unique[0].dialect_options["postgresql"]["nulls_not_distinct"], (
        "a NULL version id would slip past the constraint"
    )


def test_resume_history_has_its_own_index() -> None:
    """Finding the newest download for a person is the main lookup."""
    resume = Base.metadata.tables["resume"]
    index = next(
        item
        for item in resume.indexes
        if item.name == "ix_resume_owner_history"
    )
    expressions = list(index.expressions)

    assert getattr(expressions[0], "name", None) == "owner_id"
    assert len(expressions) == 3
