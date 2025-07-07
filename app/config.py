from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class AppConfig(BaseSettings):
    """Application configuration from environment variables."""

    # Database
    database_url: str = Field(
        default="sqlite:///./locations.db",
        json_schema_extra={"env": "DATABASE_URL"},
    )

    # Security
    secret_key: str = Field(
        default="your-secret-key-here", json_schema_extra={"env": "SECRET_KEY"}
    )

    # Application
    app_name: str = Field(
        default="Locations API", json_schema_extra={"env": "APP_NAME"}
    )
    app_version: str = Field(
        default="0.1.0", json_schema_extra={"env": "APP_VERSION"}
    )
    debug: bool = Field(default=False, json_schema_extra={"env": "DEBUG"})

    # OpenAI API
    openai_api_key: Optional[str] = Field(
        default=None, json_schema_extra={"env": "OPENAI_API_KEY"}
    )
    openai_model: str = Field(
        default="gpt-3.5-turbo-1106", json_schema_extra={"env": "OPENAI_MODEL"}
    )

    # Server
    host: str = Field(default="0.0.0.0", json_schema_extra={"env": "HOST"})
    port: int = Field(default=8000, json_schema_extra={"env": "PORT"})

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global configuration instance
config = AppConfig()
