from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "АВТОСНАБ Test Task API"
    app_version: str = "2.0.0"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/autosnab_db"
    external_server_url: str = "http://127.0.0.1:8000/result"
    external_timeout_seconds: float = Field(default=65.0, gt=0)
    emulator_min_delay_seconds: int = Field(default=0, ge=0, le=60)
    emulator_max_delay_seconds: int = Field(default=60, ge=0, le=60)
    database_connect_retries: int = Field(default=30, ge=1, le=120)
    database_retry_delay_seconds: float = Field(default=1.0, ge=0.1, le=10)
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @model_validator(mode="after")
    def validate_emulator_delay(self) -> "Settings":
        if self.emulator_min_delay_seconds > self.emulator_max_delay_seconds:
            raise ValueError(
                "EMULATOR_MIN_DELAY_SECONDS must be less than or equal to "
                "EMULATOR_MAX_DELAY_SECONDS"
            )
        return self


settings = Settings()
