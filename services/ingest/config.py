from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Everything CDK puts into the Lambda environment, checked on import."""

    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    # Absent in AWS, where the password is a short-lived IAM token.
    DB_PASSWORD: str | None = None
    DB_SSLMODE: str = "require"

    LOG_LEVEL: str = "INFO"
    METRICS_NAMESPACE: str = "CandidateSearchService"


settings = Settings()
