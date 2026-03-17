from __future__ import annotations

import pytest
from pydantic import ValidationError

from job_intake.settings import (
    REQUIRED_SUPABASE_PROJECT_REF,
    REQUIRED_SUPABASE_URL,
    Settings,
)


def clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "APP_ENV",
        "LOG_LEVEL",
        "SUPABASE_PROJECT_REF",
        "SUPABASE_URL",
        "SUPABASE_DB_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "NOTION_MCP_ENABLED",
        "NOTION_API_TOKEN",
        "NOTION_PARENT_PAGE_ID",
        "NOTION_ROOT_PAGE_ID",
        "NOTION_DATABASE_ID",
        "DEFAULT_NOTION_ROOT_PAGE_NAME",
        "DEFAULT_NOTION_DATABASE_NAME",
        ):
        monkeypatch.delenv(key, raising=False)


def isolated_settings(**kwargs: object) -> Settings:
    return Settings.from_overrides(**kwargs)


def test_settings_defaults_load_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_env(monkeypatch)

    settings = isolated_settings()

    assert settings.supabase_project_ref == REQUIRED_SUPABASE_PROJECT_REF
    assert settings.supabase_url == REQUIRED_SUPABASE_URL
    assert settings.notion.mcp_enabled is True
    assert settings.default_notion_database_name == "Student Jobs - Shortlist"


def test_settings_rejects_wrong_supabase_project_ref() -> None:
    with pytest.raises(ValidationError):
        isolated_settings(supabase_project_ref="wrong-project-ref")


def test_database_dsn_required_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_env(monkeypatch)
    settings = isolated_settings()

    with pytest.raises(RuntimeError):
        _ = settings.database_dsn_required


def test_settings_accepts_compact_or_dashed_notion_database_ids() -> None:
    compact = isolated_settings(notion_database_id="325707727e044b29aee7f6ddf331e12d")
    dashed = isolated_settings(notion_database_id="32570772-7e04-4b29-aee7-f6ddf331e12d")

    assert compact.notion_database_id_required == "325707727e044b29aee7f6ddf331e12d"
    assert dashed.notion_database_id_required == "32570772-7e04-4b29-aee7-f6ddf331e12d"


def test_settings_rejects_notion_database_id_with_trailing_newline() -> None:
    with pytest.raises(ValidationError, match="NOTION_DATABASE_ID must not contain leading or trailing whitespace"):
        isolated_settings(notion_database_id="325707727e044b29aee7f6ddf331e12d\n")


def test_settings_rejects_notion_database_id_with_embedded_whitespace() -> None:
    with pytest.raises(ValidationError, match="NOTION_DATABASE_ID must not contain embedded ASCII whitespace"):
        isolated_settings(notion_database_id="32570772 7e044b29aee7f6ddf331e12d")


def test_settings_rejects_notion_database_id_url_shape() -> None:
    with pytest.raises(ValidationError, match="NOTION_DATABASE_ID must be a raw Notion ID"):
        isolated_settings(
            notion_database_id=(
                "https://www.notion.so/325707727e044b29aee7f6ddf331e12d"
            )
        )
