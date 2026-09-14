from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Resource names and SSM prefixes shared by every stack."""

    resource_prefix: str = "candidate-search-service"

    @property
    def database_prefix(self) -> str:
        return f"/{self.resource_prefix}/database"

    @property
    def layers_prefix(self) -> str:
        return f"/{self.resource_prefix}/layers"
