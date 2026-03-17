"""Storage helpers and repository interfaces."""

from job_intake.storage.backfill import (
    apply_job_discovery_backfill,
    build_job_discovery_backfill_report,
)
from job_intake.storage.db import connect_db, db_connection, require_database_dsn
from job_intake.storage.inspection import load_pipeline_snapshot
from job_intake.storage.repositories import JobIntakeRepository

__all__ = [
    "JobIntakeRepository",
    "apply_job_discovery_backfill",
    "build_job_discovery_backfill_report",
    "connect_db",
    "db_connection",
    "load_pipeline_snapshot",
    "require_database_dsn",
]
