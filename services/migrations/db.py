"""Database connection built from the Lambda environment."""

import os

import boto3
from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine


def _password(host: str, port: int, user: str) -> str:
    """Return a short-lived IAM token, or DB_PASSWORD while bootstrapping."""
    bootstrap = os.environ.get("DB_PASSWORD")
    if bootstrap:
        return bootstrap

    return boto3.client("rds").generate_db_auth_token(
        DBHostname=host,
        Port=port,
        DBUsername=user,
    )


def url() -> URL:
    """Build the connection URL from the Lambda environment."""
    host = os.environ["DB_HOST"]
    port = int(os.environ["DB_PORT"])
    user = os.environ["DB_USER"]

    return URL.create(
        drivername="postgresql+psycopg",
        username=user,
        password=_password(host=host, port=port, user=user),
        host=host,
        port=port,
        database=os.environ["DB_NAME"],
    )


def engine() -> Engine:
    """Return an engine over TLS, which RDS requires for IAM tokens."""
    return create_engine(url(), connect_args={"sslmode": "require"})
