from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID

from job_intake.models import (
    CanonicalJob,
    JobClassification,
    JobDiscovery,
    PipelineRun,
    SearchDefinition,
)
from job_intake.notion.client import NotionPageRecord
from job_intake.notion.sync import NotionSyncService
from job_intake.orchestration import JobIntakePipeline

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "linkedin"


class FakePipelineRepository:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.discovery_records: list[tuple[JobDiscovery, UUID | None, UUID | None]] = []
        self.pipeline_updates: list[dict[str, object]] = []

    def insert_pipeline_run(self, pipeline_run: PipelineRun) -> UUID:
        self.calls.append(f"insert_pipeline_run:{pipeline_run.stage}")
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
        self.calls.append(f"update_pipeline_run:{status}")
        self.pipeline_updates.append(
            {
                "pipeline_run_id": pipeline_run_id,
                "status": status,
                "finished_at": finished_at,
                "counters": counters,
                "summary": summary,
            }
        )

    def upsert_search_definition(self, definition: SearchDefinition) -> UUID:
        self.calls.append(f"upsert_search_definition:{definition.name}")
        return UUID("00000000-0000-4000-8000-000000000002")

    def insert_job_discovery(
        self,
        discovery: JobDiscovery,
        *,
        pipeline_run_id: UUID | None = None,
        job_id: UUID | None = None,
    ) -> UUID:
        self.calls.append(f"insert_job_discovery:{discovery.discovery_url}")
        self.discovery_records.append((discovery, pipeline_run_id, job_id))
        return UUID("00000000-0000-4000-8000-000000000003")

    def upsert_job(self, job: CanonicalJob) -> UUID:
        self.calls.append(f"upsert_job:{job.canonical_job_key}")
        return UUID("00000000-0000-4000-8000-000000000004")

    def upsert_job_classification(
        self,
        job_id: UUID,
        classification: JobClassification,
    ) -> UUID:
        self.calls.append(f"upsert_job_classification:{classification.role_family.value}")
        return UUID("00000000-0000-4000-8000-000000000005")


class FakePipelineSyncClient:
    def __init__(self) -> None:
        self.pages: dict[str, NotionPageRecord] = {}

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
        content_blocks: tuple[object, ...] | list[object],
    ) -> NotionPageRecord:
        page = NotionPageRecord(
            id="page-1",
            properties=properties.copy(),
            managed_blocks=tuple(content_blocks),
        )
        self.pages[str(properties["Canonical Job Key"])] = page
        return page

    def update_database_page(
        self,
        *,
        page_id: str,
        properties: dict[str, object | None],
        content_blocks: tuple[object, ...] | list[object],
    ) -> NotionPageRecord:
        page = NotionPageRecord(
            id=page_id,
            properties=properties.copy(),
            managed_blocks=tuple(content_blocks),
        )
        self.pages[str(properties["Canonical Job Key"])] = page
        return page


def read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def test_run_fixture_slice_processes_discovery_detail_classification_and_sync() -> None:
    repository = FakePipelineRepository()
    sync_service = NotionSyncService(FakePipelineSyncClient(), database_id="database-id")
    pipeline = JobIntakePipeline(repository=repository, sync_service=sync_service)
    first_detail_url = (
        "https://www.linkedin.com/jobs/view/4185654374/"
        "?trk=public_jobs_jserp-result_search-card"
    )

    summary = pipeline.run_fixture_slice(
        discovery_html_by_search_name={
            "berlin_data_engineering_student": read_fixture("list_search_results.html"),
        },
        detail_html_by_url={
            first_detail_url: read_fixture("job_detail.html"),
            "https://www.linkedin.com/jobs/view/4185654375/": read_fixture(
                "job_detail_missing_optional_fields.html"
            ),
        },
    )

    assert summary.searches == 1
    assert summary.discoveries == 2
    assert summary.details == 2
    assert summary.classified == 2
    assert summary.shortlisted == 2
    assert summary.synced_created == 2
    assert summary.errors == []
    assert repository.calls[0] == "insert_pipeline_run:pipeline"
    assert repository.calls[-1] == "update_pipeline_run:succeeded"
    assert isinstance(repository.pipeline_updates[-1]["finished_at"], datetime)
    assert len(repository.discovery_records) == 2
    assert all(
        record[0].search_definition_id == UUID("00000000-0000-4000-8000-000000000002")
        for record in repository.discovery_records
    )
    assert all(
        record[2] == UUID("00000000-0000-4000-8000-000000000004")
        for record in repository.discovery_records
    )


def test_run_fixture_slice_records_missing_detail_errors_explicitly() -> None:
    repository = FakePipelineRepository()
    pipeline = JobIntakePipeline(repository=repository)

    summary = pipeline.run_fixture_slice(
        discovery_html_by_search_name={
            "berlin_data_engineering_student": read_fixture("list_search_results.html"),
        },
        detail_html_by_url={},
    )

    assert summary.discoveries == 2
    assert summary.details == 0
    assert len(summary.errors) == 2
    assert "Missing detail HTML" in summary.errors[0]
    assert isinstance(repository.pipeline_updates[-1]["finished_at"], datetime)
    assert len(repository.discovery_records) == 2
    assert all(
        record[0].search_definition_id == UUID("00000000-0000-4000-8000-000000000002")
        for record in repository.discovery_records
    )
    assert all(record[2] is None for record in repository.discovery_records)
