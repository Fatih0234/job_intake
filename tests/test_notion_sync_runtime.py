from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from job_intake.models import (
    CanonicalJob,
    JobClassification,
    NotionSyncState,
    PipelineRun,
    RoleFamily,
    StudentFit,
)
from job_intake.models.storage import ClassifiedJobRecord
from job_intake.notion.client import NotionPageRecord
from job_intake.notion.mapper import build_notion_job_properties
from job_intake.notion.sync import NotionSyncService
from job_intake.orchestration.notion_sync_runtime import (
    NotionShortlistSyncRunner,
    _checksum_payload,
)


class FakeSyncRuntimeRepository:
    def __init__(self, records: list[ClassifiedJobRecord]) -> None:
        self.records = records
        self.sync_state_updates: list[dict[str, object | None]] = []
        self.pipeline_updates: list[dict[str, object]] = []

    def insert_pipeline_run(self, pipeline_run: PipelineRun) -> UUID:
        return UUID("00000000-0000-4000-8000-000000000001")

    def update_pipeline_run(
        self,
        *,
        pipeline_run_id: UUID,
        status: str,
        finished_at: object | None = None,
        counters: dict[str, int] | None = None,
        summary: dict[str, object] | None = None,
    ) -> None:
        self.pipeline_updates.append(
            {
                "pipeline_run_id": pipeline_run_id,
                "status": status,
                "finished_at": finished_at,
                "counters": counters,
                "summary": summary,
            }
        )

    def list_shortlisted_jobs_for_notion_sync(self, *, limit: int) -> list[ClassifiedJobRecord]:
        return self.records[:limit]

    def upsert_notion_sync_state(
        self,
        *,
        job_id: UUID,
        notion_page_id: str | None,
        sync_status: str,
        last_error: str | None = None,
        payload_checksum: str | None = None,
    ) -> UUID:
        self.sync_state_updates.append(
            {
                "job_id": job_id,
                "notion_page_id": notion_page_id,
                "sync_status": sync_status,
                "last_error": last_error,
                "payload_checksum": payload_checksum,
            }
        )
        return UUID("00000000-0000-4000-8000-000000000002")


class FakeRuntimeSyncClient:
    def __init__(self) -> None:
        self.pages: dict[str, NotionPageRecord] = {}
        self.creates = 0
        self.updates = 0

    def find_page_by_canonical_job_key(
        self,
        *,
        database_id: str,
        canonical_job_key: str,
    ) -> NotionPageRecord | None:
        return self.pages.get(canonical_job_key)

    def create_database_page(
        self,
        *,
        database_id: str,
        properties: dict[str, object | None],
    ) -> NotionPageRecord:
        self.creates += 1
        page = NotionPageRecord(id="page-1", properties=properties.copy())
        self.pages[str(properties["Canonical Job Key"])] = page
        return page

    def update_database_page(
        self,
        *,
        page_id: str,
        properties: dict[str, object | None],
    ) -> NotionPageRecord:
        self.updates += 1
        page = NotionPageRecord(id=page_id, properties=properties.copy())
        self.pages[str(properties["Canonical Job Key"])] = page
        return page


def build_record(*, sync_state: NotionSyncState | None = None) -> ClassifiedJobRecord:
    job = CanonicalJob(
        id=UUID("00000000-0000-4000-8000-000000000010"),
        canonical_job_key="linkedin:4185654374",
        external_job_id="4185654374",
        source_job_url="https://www.linkedin.com/jobs/view/4185654374/",
        normalized_job_url="https://linkedin.com/jobs/view/4185654374",
        title="Werkstudent Data Engineer",
        company="Acme Analytics",
        city="Berlin",
        description_text="Build ETL pipelines with SQL and Airflow.",
        posted_text="2 days ago",
        source_search_name="berlin_data_engineering_student",
        last_seen_at=datetime(2026, 3, 17, 10, 0, tzinfo=UTC),
    )
    classification = JobClassification(
        job_id=job.id,
        student_fit=StudentFit.TARGET_STUDENT_JOB,
        role_family=RoleFamily.DATA_ENGINEERING,
        shortlist_decision=True,
        shortlist_reason="city in scope; student fit eligible",
        signals={},
    )
    return ClassifiedJobRecord(
        job=job,
        classification=classification,
        notion_sync_state=sync_state,
    )


def test_notion_sync_runtime_runner_creates_pages_and_persists_sync_state() -> None:
    repository = FakeSyncRuntimeRepository([build_record()])
    sync_client = FakeRuntimeSyncClient()
    sync_service = NotionSyncService(sync_client, database_id="database-id")
    runner = NotionShortlistSyncRunner(repository, sync_service=sync_service)

    summary = runner.run(limit_jobs=1)

    assert summary.jobs_attempted == 1
    assert summary.synced_created == 1
    assert summary.synced_updated == 0
    assert summary.synced_skipped == 0
    assert summary.sync_failed == 0
    assert repository.sync_state_updates[0]["sync_status"] == "synced"
    assert repository.sync_state_updates[0]["notion_page_id"] == "page-1"
    assert repository.pipeline_updates[-1]["status"] == "succeeded"


def test_notion_sync_runtime_runner_skips_when_payload_checksum_matches() -> None:
    record = build_record()
    checksum = _checksum_payload(build_notion_job_properties(record.job, record.classification))
    record.notion_sync_state = NotionSyncState(
        job_id=UUID("00000000-0000-4000-8000-000000000010"),
        notion_page_id="page-1",
        sync_status="synced",
        payload_checksum=checksum,
    )
    repository = FakeSyncRuntimeRepository([record])
    sync_client = FakeRuntimeSyncClient()
    sync_service = NotionSyncService(sync_client, database_id="database-id")
    runner = NotionShortlistSyncRunner(repository, sync_service=sync_service)

    summary = runner.run(limit_jobs=1)

    assert summary.synced_created == 0
    assert summary.synced_updated == 0
    assert summary.synced_skipped == 1
    assert sync_client.creates == 0
    assert sync_client.updates == 0
