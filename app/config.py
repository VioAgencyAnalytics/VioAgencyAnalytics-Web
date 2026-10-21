from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeMode(BaseSettings):
    app_env: Literal["development", "test", "production"] = "development"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class Settings(RuntimeMode):
    app_name: str = Field(default="KDH Marketing Dashboard")
    debug: bool = False
    database_url: str = "postgresql://postgres:postgres@localhost:5432/kdh_report"
        # =====================================================
    # KDH REPORT ADMIN - INTERNAL REPORT API
    # =====================================================

    report_admin_base_url: str = (
        "http://127.0.0.1:8090"
    )

    report_service_token: SecretStr = SecretStr("")
    # Browser origins; report_admin_base_url remains backend/internal only.
    report_admin_public_url: str = 'http://localhost:8090'
    report_new_public_url: str = 'http://localhost:8080'

    # Explicit local dual-Admin mode. Each origin retains its own backend and
    # host-only browser cookies; selecting an origin never grants report access.
    report_vio_viewer_enabled: bool = False
    report_vio_admin_base_url: str = ''
    report_vio_admin_public_url: str = ''
    report_vio_new_public_url: str = ''
    report_vio_service_token: SecretStr = SecretStr('')

    report_request_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
        le=30,
    )
    # Temporary developer access; production is denied even if enabled.
    report_preview_enabled: bool = False
    report_preview_username: str = ""
    report_preview_password: SecretStr = SecretStr("")
    report_preview_allowed_ids: list[str] = Field(default_factory=list)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_runtime_mode() -> RuntimeMode:
    # Route isolation must not depend on unrelated provider/debug configuration.
    return RuntimeMode()
