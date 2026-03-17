from __future__ import annotations

import pytest

from job_intake.settings import Settings
from job_intake.storage.db import require_database_dsn


def test_require_database_dsn_accepts_pooler_host() -> None:
    settings = Settings.from_overrides(
        supabase_db_url=(
            "postgresql://postgres.aashdnhoiqqdhpdedaab:secret@"
            "aws-1-eu-west-1.pooler.supabase.com:5432/postgres"
        ),
    )

    assert require_database_dsn(settings) == settings.supabase_db_url


def test_require_database_dsn_raises_when_missing() -> None:
    settings = Settings.from_overrides()

    with pytest.raises(RuntimeError, match="SUPABASE_DB_URL is required"):
        require_database_dsn(settings)


def test_require_database_dsn_rejects_direct_supabase_host() -> None:
    settings = Settings.from_overrides(
        supabase_db_url=(
            "postgresql://postgres.aashdnhoiqqdhpdedaab:secret@"
            "db.aashdnhoiqqdhpdedaab.supabase.co:5432/postgres"
        ),
    )

    with pytest.raises(RuntimeError, match="pooler"):
        require_database_dsn(settings)

