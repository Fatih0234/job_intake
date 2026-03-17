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
    def __init__(
        self,
        row: dict[str, Any] | None = None,
        rows: list[dict[str, Any]] | None = None,
    ) -> None:
        self.row = row
        self.rows = rows or []

    def fetchone(self) -> dict[str, Any] | None:
        return self.row

    def fetchall(self) -> list[dict[str, Any]]:
        return self.rows


class FakeConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.next_id = UUID("00000000-0000-4000-8000-000000000001")
        self.fetchall_rows: list[dict[str, Any]] = []

    def execute(self, sql: str, params: dict[str, Any]) -> FakeCursor:
        self.calls.append((sql, params))
        if sql.lstrip().lower().startswith("select"):
            return FakeCursor(rows=self.fetchall_rows)
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


def test_list_latest_unlinked_job_discoveries_uses_distinct_query_and_limit() -> None:
    connection = FakeConnection()
    connection.fetchall_rows = [
        {
            "id": "00000000-0000-4000-8000-000000000011",
            "search_definition_id": None,
            "platform": "linkedin",
            "external_job_id": "4185654374",
            "discovery_url": "https://www.linkedin.com/jobs/view/4185654374/",
            "rank_position": 1,
            "discovered_at": datetime(2026, 3, 17, 9, 0, tzinfo=UTC),
            "raw_payload": {"source_search_name": "berlin_data_engineering_student"},
        }
    ]

    repository = JobIntakeRepository(connection)
    discoveries = repository.list_latest_unlinked_job_discoveries(limit=5)

    assert len(discoveries) == 1
    assert discoveries[0].external_job_id == "4185654374"
    assert "distinct on" in connection.calls[0][0].lower()
    assert connection.calls[0][1] == {"limit": 5}


def test_update_job_discovery_job_link_updates_existing_discovery() -> None:
    connection = FakeConnection()
    repository = JobIntakeRepository(connection)

    repository.update_job_discovery_job_link(
        discovery_id=UUID("00000000-0000-4000-8000-000000000011"),
        job_id=UUID("00000000-0000-4000-8000-000000000012"),
    )

    sql, params = connection.calls[0]
    assert "update job_discoveries" in sql.lower()
    assert params["discovery_id"] == UUID("00000000-0000-4000-8000-000000000011")
    assert params["job_id"] == UUID("00000000-0000-4000-8000-000000000012")


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


def test_list_latest_unclassified_jobs_returns_canonical_jobs() -> None:
    connection = FakeConnection()
    connection.fetchall_rows = [
        {
            "id": "00000000-0000-4000-8000-000000000021",
            "canonical_job_key": "linkedin:4185654374",
            "platform": "linkedin",
            "external_job_id": "4185654374",
            "source_job_url": "https://www.linkedin.com/jobs/view/4185654374/",
            "normalized_job_url": "https://linkedin.com/jobs/view/4185654374",
            "title": "Data Engineering Working Student",
            "company": "Acme Analytics",
            "city": "Berlin",
            "country": "Germany",
            "location_raw": "Berlin, Germany",
            "description_text": "Build ETL pipelines.",
            "employment_type": None,
            "seniority": None,
            "posted_text": "2 days ago",
            "posted_at": None,
            "first_seen_at": datetime(2026, 3, 17, 9, 0, tzinfo=UTC),
            "last_seen_at": datetime(2026, 3, 17, 10, 0, tzinfo=UTC),
            "source_search_name": "berlin_data_engineering_student",
            "metadata": {},
        }
    ]

    repository = JobIntakeRepository(connection)
    jobs = repository.list_latest_unclassified_jobs(limit=10)

    assert len(jobs) == 1
    assert jobs[0].canonical_job_key == "linkedin:4185654374"
    assert "left join job_classifications" in connection.calls[0][0].lower()
    assert connection.calls[0][1] == {"limit": 10}


def test_list_shortlisted_jobs_for_notion_sync_returns_joined_records() -> None:
    connection = FakeConnection()
    connection.fetchall_rows = [
        {
            "job_id": "00000000-0000-4000-8000-000000000031",
            "canonical_job_key": "linkedin:4185654374",
            "platform": "linkedin",
            "external_job_id": "4185654374",
            "source_job_url": "https://www.linkedin.com/jobs/view/4185654374/",
            "normalized_job_url": "https://linkedin.com/jobs/view/4185654374",
            "title": "Data Engineering Working Student",
            "company": "Acme Analytics",
            "city": "Berlin",
            "country": "Germany",
            "location_raw": "Berlin, Germany",
            "description_text": "Build ETL pipelines.",
            "employment_type": None,
            "seniority": None,
            "posted_text": "2 days ago",
            "posted_at": None,
            "first_seen_at": datetime(2026, 3, 17, 9, 0, tzinfo=UTC),
            "last_seen_at": datetime(2026, 3, 17, 10, 0, tzinfo=UTC),
            "source_search_name": "berlin_data_engineering_student",
            "metadata": {},
            "classification_id": "00000000-0000-4000-8000-000000000032",
            "student_fit": "target_student_job",
            "role_family": "data_engineering",
            "shortlist_decision": True,
            "shortlist_reason": "city in scope; student fit eligible",
            "rule_version": "v1",
            "signals": {"student_fit": {"positive_terms": ["Werkstudent"]}},
            "notion_sync_state_id": "00000000-0000-4000-8000-000000000033",
            "notion_page_id": "page-123",
            "sync_status": "synced",
            "last_attempted_at": datetime(2026, 3, 17, 11, 0, tzinfo=UTC),
            "last_synced_at": datetime(2026, 3, 17, 11, 0, tzinfo=UTC),
            "last_error": None,
            "payload_checksum": "abc123",
        }
    ]

    repository = JobIntakeRepository(connection)
    records = repository.list_shortlisted_jobs_for_notion_sync(limit=5)

    assert len(records) == 1
    assert records[0].job.id == UUID("00000000-0000-4000-8000-000000000031")
    assert records[0].classification.student_fit is StudentFit.TARGET_STUDENT_JOB
    assert records[0].notion_sync_state is not None
    assert records[0].notion_sync_state.payload_checksum == "abc123"
    assert "left join notion_sync_state" in connection.calls[0][0].lower()


def test_upsert_notion_sync_state_persists_status_and_checksum() -> None:
    connection = FakeConnection()
    repository = JobIntakeRepository(connection)

    repository.upsert_notion_sync_state(
        job_id=UUID("00000000-0000-4000-8000-000000000041"),
        notion_page_id="page-1",
        sync_status="synced",
        payload_checksum="deadbeef",
    )

    sql, params = connection.calls[0]
    assert "insert into notion_sync_state" in sql.lower()
    assert params["sync_status"] == "synced"
    assert params["payload_checksum"] == "deadbeef"
