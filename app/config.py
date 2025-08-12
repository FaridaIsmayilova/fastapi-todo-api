# app/config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # PostgreSQL
    POSTGRES_USER: str = Field("todo_user")
    POSTGRES_PASSWORD: str = Field("StrongPassword123!")
    POSTGRES_DB: str = Field("todo")
    POSTGRES_HOST: str = Field("localhost")
    POSTGRES_PORT: int = Field(5432)

    # JWT / Auth
    SECRET_KEY: str = Field("dev-secret-change-me")   # override in env for prod
    ALGORITHM: str = Field("HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(1440)

    # Load from environment and (optionally) a .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

def settings() -> Settings:
    return Settings()
