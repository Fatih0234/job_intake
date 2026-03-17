"""Application settings and local environment loading."""

from __future__ import annotations

from functools import cached_property, lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REQUIRED_SUPABASE_PROJECT_REF = "aashdnhoiqqdhpdedaab"
REQUIRED_SUPABASE_URL = "https://aashdnhoiqqdhpdedaab.supabase.co"


class AppConfig(BaseModel):
    env: str
    log_level: str


class SupabaseConfig(BaseModel):
    project_ref: str
    url: str
    db_url: str | None = None
    anon_key: str | None = None
    service_role_key: str | None = None


class NotionConfig(BaseModel):
    mcp_enabled: bool
    api_token: str | None = None
    parent_page_id: str | None = None
    root_page_id: str | None = None
    database_id: str | None = None
    default_root_page_name: str
    default_database_name: str


class Settings(BaseSettings):
    """Single settings entrypoint for scripts and future pipeline code."""

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: str = Field(default="local", validation_alias="APP_ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    supabase_project_ref: str = Field(
        default=REQUIRED_SUPABASE_PROJECT_REF,
        validation_alias="SUPABASE_PROJECT_REF",
    )
    supabase_url: str = Field(default=REQUIRED_SUPABASE_URL, validation_alias="SUPABASE_URL")
    supabase_db_url: str | None = Field(default=None, validation_alias="SUPABASE_DB_URL")
    supabase_anon_key: str | None = Field(default=None, validation_alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str | None = Field(
        default=None,
        validation_alias="SUPABASE_SERVICE_ROLE_KEY",
    )

    notion_mcp_enabled: bool = Field(default=True, validation_alias="NOTION_MCP_ENABLED")
    notion_api_token: str | None = Field(default=None, validation_alias="NOTION_API_TOKEN")
    notion_parent_page_id: str | None = Field(
        default=None,
        validation_alias="NOTION_PARENT_PAGE_ID",
    )
    notion_root_page_id: str | None = Field(default=None, validation_alias="NOTION_ROOT_PAGE_ID")
    notion_database_id: str | None = Field(default=None, validation_alias="NOTION_DATABASE_ID")
    default_notion_root_page_name: str = Field(
        default="Student Job Intake",
        validation_alias="DEFAULT_NOTION_ROOT_PAGE_NAME",
    )
    default_notion_database_name: str = Field(
        default="Student Jobs - Shortlist",
        validation_alias="DEFAULT_NOTION_DATABASE_NAME",
    )

    @model_validator(mode="after")
    def validate_fixed_supabase_project(self) -> Settings:
        if self.supabase_project_ref != REQUIRED_SUPABASE_PROJECT_REF:
            raise ValueError(
                "SUPABASE_PROJECT_REF must remain "
                f"{REQUIRED_SUPABASE_PROJECT_REF!r} for this repo.",
            )
        if self.supabase_url != REQUIRED_SUPABASE_URL:
            raise ValueError(f"SUPABASE_URL must remain {REQUIRED_SUPABASE_URL!r} for this repo.")
        self.log_level = self.log_level.upper()
        return self

    @property
    def app(self) -> AppConfig:
        return AppConfig(env=self.app_env, log_level=self.log_level)

    @property
    def supabase(self) -> SupabaseConfig:
        return SupabaseConfig(
            project_ref=self.supabase_project_ref,
            url=self.supabase_url,
            db_url=self.supabase_db_url,
            anon_key=self.supabase_anon_key,
            service_role_key=self.supabase_service_role_key,
        )

    @property
    def notion(self) -> NotionConfig:
        return NotionConfig(
            mcp_enabled=self.notion_mcp_enabled,
            api_token=self.notion_api_token,
            parent_page_id=self.notion_parent_page_id,
            root_page_id=self.notion_root_page_id,
            database_id=self.notion_database_id,
            default_root_page_name=self.default_notion_root_page_name,
            default_database_name=self.default_notion_database_name,
        )

    @cached_property
    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @cached_property
    def configs_dir(self) -> Path:
        return self.repo_root / "configs"

    @cached_property
    def supabase_migrations_dir(self) -> Path:
        return self.repo_root / "supabase" / "migrations"

    @property
    def database_dsn_required(self) -> str:
        if not self.supabase_db_url:
            raise RuntimeError(
                "SUPABASE_DB_URL is required for database operations. "
                "Fill it in locally before using storage helpers.",
            )
        return self.supabase_db_url

    def missing_local_values(self) -> dict[str, list[str]]:
        required_for_db = []
        optional_or_later = []

        if not self.supabase_db_url:
            required_for_db.append("SUPABASE_DB_URL")

        if not self.supabase_anon_key:
            optional_or_later.append("SUPABASE_ANON_KEY")
        if not self.supabase_service_role_key:
            optional_or_later.append("SUPABASE_SERVICE_ROLE_KEY")
        if not self.notion_api_token:
            optional_or_later.append("NOTION_API_TOKEN")
        if not self.notion_parent_page_id:
            optional_or_later.append("NOTION_PARENT_PAGE_ID")
        if not self.notion_root_page_id:
            optional_or_later.append("NOTION_ROOT_PAGE_ID")
        if not self.notion_database_id:
            optional_or_later.append("NOTION_DATABASE_ID")

        return {
            "required_for_db": required_for_db,
            "optional_or_later": optional_or_later,
        }

    @classmethod
    def from_overrides(cls, **values: Any) -> Settings:
        """Build validated settings from explicit overrides without reading env files."""
        return cls(_env_file=None, **values)  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
