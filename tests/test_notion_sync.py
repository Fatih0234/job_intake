from __future__ import annotations

from datetime import UTC, datetime

from job_intake.models import CanonicalJob, JobClassification, RoleFamily, StudentFit
from job_intake.notion.client import NotionPageRecord
from job_intake.notion.mapper import build_notion_job_properties
from job_intake.notion.sync import NotionSyncCandidate, NotionSyncService


class FakeSyncClient:
    def __init__(self) -> None:
        self.pages: dict[str, NotionPageRecord] = {}
        self.created_pages: list[dict[str, object | None]] = []
        self.updated_pages: list[tuple[str, dict[str, object | None]]] = []

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
        page = NotionPageRecord(
            id=f"page-{len(self.pages) + 1}",
            properties=properties.copy(),
        )
        self.pages[str(properties["Canonical Job Key"])] = page
        self.created_pages.append(properties.copy())
        return page

    def update_database_page(
        self,
        *,
        page_id: str,
        properties: dict[str, object | None],
    ) -> NotionPageRecord:
        canonical_job_key = str(properties["Canonical Job Key"])
        page = NotionPageRecord(id=page_id, properties=properties.copy())
        self.pages[canonical_job_key] = page
        self.updated_pages.append((page_id, properties.copy()))
        return page


def build_candidate(
    *,
    title: str = "Data Engineering Working Student",
    posted_text: str | None = "2 days ago",
    shortlist_decision: bool = True,
    student_fit: StudentFit = StudentFit.TARGET_STUDENT_JOB,
) -> NotionSyncCandidate:
    return NotionSyncCandidate(
        job=CanonicalJob(
            canonical_job_key="linkedin:4185654374",
            external_job_id="4185654374",
            source_job_url="https://www.linkedin.com/jobs/view/4185654374/",
            normalized_job_url="https://linkedin.com/jobs/view/4185654374",
            title=title,
            company="Acme Analytics",
            city="Berlin",
            description_text="Build ETL pipelines with Airflow.",
            posted_text=posted_text,
            source_search_name="berlin_data_engineering_student",
            last_seen_at=datetime(2026, 3, 17, 9, 0, tzinfo=UTC),
        ),
        classification=JobClassification(
            student_fit=student_fit,
            role_family=RoleFamily.DATA_ENGINEERING,
            shortlist_decision=shortlist_decision,
            shortlist_reason=(
                "city in scope; role family in scope; "
                "required fields present; student fit eligible"
            ),
        ),
    )


def test_build_notion_job_properties_excludes_manual_fields() -> None:
    candidate = build_candidate()

    properties = build_notion_job_properties(candidate.job, candidate.classification)

    assert "Priority" not in properties
    assert "Review Status" not in properties
    assert properties["Canonical Job Key"] == "linkedin:4185654374"


def test_build_notion_job_properties_uses_sanitized_job_url() -> None:
    candidate = build_candidate()
    candidate.job = CanonicalJob(
        **{
            **candidate.job.model_dump(),
            "source_job_url": "https://www.linkedin.com/jobs/view/\n4185654374/",
            "normalized_job_url": "https://linkedin.com/jobs/view/\n4185654374",
        }
    )

    properties = build_notion_job_properties(candidate.job, candidate.classification)

    assert properties["Job URL"] == "https://linkedin.com/jobs/view/4185654374"


def test_sync_shortlisted_jobs_creates_pages_for_new_target_candidates() -> None:
    client = FakeSyncClient()
    service = NotionSyncService(client, database_id="database-id")

    result = service.sync_shortlisted_jobs([build_candidate()])

    assert result.created == 1
    assert result.updated == 0
    assert result.skipped == 0


def test_sync_shortlisted_jobs_skips_when_managed_fields_are_unchanged() -> None:
    client = FakeSyncClient()
    service = NotionSyncService(client, database_id="database-id")
    candidate = build_candidate()

    service.sync_shortlisted_jobs([candidate])
    result = service.sync_shortlisted_jobs([candidate])

    assert result.created == 0
    assert result.updated == 0
    assert result.skipped == 1


def test_sync_shortlisted_jobs_updates_existing_pages_when_managed_fields_change() -> None:
    client = FakeSyncClient()
    service = NotionSyncService(client, database_id="database-id")
    original = build_candidate()
    changed = build_candidate(posted_text="today")

    service.sync_shortlisted_jobs([original])
    result = service.sync_shortlisted_jobs([changed])

    assert result.created == 0
    assert result.updated == 1
    assert result.skipped == 0


def test_sync_shortlisted_jobs_skips_possible_student_jobs_under_strict_default() -> None:
    client = FakeSyncClient()
    service = NotionSyncService(client, database_id="database-id")

    result = service.sync_shortlisted_jobs(
        [
            build_candidate(
                student_fit=StudentFit.POSSIBLE_STUDENT_JOB,
                shortlist_decision=True,
            )
        ]
    )

    assert result.created == 0
    assert result.updated == 0
    assert result.skipped == 1
