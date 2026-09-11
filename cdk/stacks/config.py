from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    resource_prefix: str = "candidate-search-service"

    @property
    def database_prefix(self) -> str:
        return f"/{self.resource_prefix}/database"
