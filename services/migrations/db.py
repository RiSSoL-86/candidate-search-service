import boto3
from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine

from config import settings


def _password() -> str:
    """Return a short-lived IAM token, or DB_PASSWORD while bootstrapping."""
    if settings.DB_PASSWORD:
        return settings.DB_PASSWORD

    return boto3.client("rds").generate_db_auth_token(
        DBHostname=settings.DB_HOST,
        Port=settings.DB_PORT,
        DBUsername=settings.DB_USER,
    )


def url() -> URL:
    """Build the connection URL from the settings."""
    return URL.create(
        drivername="postgresql+psycopg",
        username=settings.DB_USER,
        password=_password(),
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
    )


def engine() -> Engine:
    """Return an engine over TLS, which RDS requires for IAM tokens."""
    return create_engine(url(), connect_args={"sslmode": settings.DB_SSLMODE})
