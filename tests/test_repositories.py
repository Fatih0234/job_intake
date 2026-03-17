from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from job_intake.models import (
    CanonicalJob,
    JobClassification,
    JobDiscovery,
    PipelineRun,
    RoleFamily,
    SearchDefinition,
    StudentFit,
)
from job_intake.storage.repositories import JobIntakeRepository


class FakeCursor:
    def __init__(self, row: dict[str, Any] | None = None) -> None:
        self.row = row

    def fetchone(self) -> dict[str, Any] | None:
        return self.row


class FakeConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.next_id = UUID("00000000-0000-4000-8000-000000000001")

    def execute(self, sql: str, params: dict[str, Any]) -> FakeCursor:
        self.calls.append((sql, params))
        if "returning id" in sql.lower():
            return FakeCursor({"id": str(self.next_id)})
        return FakeCursor(None)


def test_upsert_search_definition_persists_filters_inside_config_payload() -> None:
    connection = FakeConnection()
    repository = JobIntakeRepository(connection)

    repository.upsert_search_definition(
        SearchDefinition(
            name="berlin_data_engineering_student",
            city="Berlin",
            role_family=RoleFamily.DATA_ENGINEERING,
            keywords=["Werkstudent Data Engineering"],
            filters={"f_TPR": "r604800"},
            metadata={"source": "repo-config"},
        )
    )

    _, params = connection.calls[0]
    assert params["keywords"].obj == ["Werkstudent Data Engineering"]
    assert params["config_payload"].obj == {
        "filters": {"f_TPR": "r604800"},
        "source": "repo-config",
    }


def test_insert_pipeline_run_and_update_pipeline_run_emit_expected_sql() -> None:
    connection = FakeConnection()
    repository = JobIntakeRepository(connection)

    pipeline_run_id = repository.insert_pipeline_run(
        PipelineRun(
            stage="discovery",
            status="running",
            started_at=datetime(2026, 3, 17, 9, 0, tzinfo=UTC),
            counters={"searches": 5},
            summary={"source": "linkedin"},
        )
    )

    repository.update_pipeline_run(
        pipeline_run_id=pipeline_run_id,
        status="succeeded",
        finished_at=datetime(2026, 3, 17, 9, 15, tzinfo=UTC),
        counters={"discoveries": 12},
        summary={"errors": 0},
    )

    assert pipeline_run_id == connection.next_id
    assert "insert into pipeline_runs" in connection.calls[0][0].lower()
    assert "update pipeline_runs" in connection.calls[1][0].lower()


def test_insert_job_discovery_uses_discovery_url_and_raw_payload() -> None:
    connection = FakeConnection()
    repository = JobIntakeRepository(connection)

    repository.insert_job_discovery(
        JobDiscovery(
            discovery_url="https://www.linkedin.com/jobs/view/4185654374/",
            external_job_id="4185654374",
            rank_position=1,
            raw_payload={"title": "Data Engineering Working Student"},
        ),
    )

    _, params = connection.calls[0]
    assert params["discovery_url"] == "https://www.linkedin.com/jobs/view/4185654374/"
    assert params["raw_payload"].obj == {"title": "Data Engineering Working Student"}


def test_upsert_job_and_classification_keep_canonical_key_and_rule_fields() -> None:
    connection = FakeConnection()
    repository = JobIntakeRepository(connection)

    job_id = repository.upsert_job(
        CanonicalJob(
            canonical_job_key="linkedin:4185654374",
            external_job_id="4185654374",
            source_job_url="https://www.linkedin.com/jobs/view/4185654374/",
            normalized_job_url="https://linkedin.com/jobs/view/4185654374",
            title="Data Engineering Working Student",
            company="Acme Analytics",
            city="Berlin",
        )
    )
    repository.upsert_job_classification(
        job_id,
        JobClassification(
            student_fit=StudentFit.TARGET_STUDENT_JOB,
            role_family=RoleFamily.DATA_ENGINEERING,
            shortlist_decision=True,
            shortlist_reason="student terms and role-family match",
            signals={"positive_terms": ["working student"]},
        ),
    )

    assert job_id == connection.next_id
    assert "insert into jobs" in connection.calls[0][0].lower()
    assert "insert into job_classifications" in connection.calls[1][0].lower()
