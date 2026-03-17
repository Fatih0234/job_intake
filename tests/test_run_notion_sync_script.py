from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from pydantic import ValidationError

from job_intake.settings import Settings

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_notion_sync.py"
SPEC = importlib.util.spec_from_file_location("run_notion_sync_script", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_parse_args_defaults_limit_jobs() -> None:
    args = MODULE.parse_args([])

    assert args.limit_jobs == 25


def test_parse_args_rejects_non_positive_limit_jobs() -> None:
    with pytest.raises(SystemExit):
        MODULE.parse_args(["--limit-jobs", "0"])


def test_main_exits_before_db_work_when_notion_database_id_is_malformed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_parse_args = MODULE.parse_args
    monkeypatch.setattr(MODULE, "parse_args", lambda argv=None: original_parse_args([]))
    monkeypatch.setattr(MODULE, "configure_logging", lambda: None)

    def bad_settings() -> Settings:
        return Settings.from_overrides(
            notion_database_id="325707727e044b29aee7f6ddf331e12d\n",
            notion_api_token="secret-token",
        )

    monkeypatch.setattr(MODULE, "get_settings", bad_settings)

    def should_not_connect() -> None:
        raise AssertionError("db_connection should not be called for invalid Notion config")

    monkeypatch.setattr(MODULE, "db_connection", should_not_connect)

    with pytest.raises(ValidationError, match="NOTION_DATABASE_ID must not contain leading or trailing whitespace"):
        MODULE.main()
