from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Culinary Blog API"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://culinary:culinary@localhost:5432/culinary_blog"
    frontend_origin: str = "http://localhost:3000"
    jwt_secret: SecretStr = SecretStr("development-only-change-me")

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    @property
    def frontend_origins(self) -> list[str]:
        """Return configured CORS origins plus the local hot-reload origin in development."""
        origins = [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]
        if self.environment.lower() == "development":
            origins.extend(["http://localhost:3000", "http://localhost:3001"])
        return list(dict.fromkeys(origins))


@lru_cache
def get_settings() -> Settings:
    return Settings()
