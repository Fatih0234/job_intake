from __future__ import annotations

from datetime import UTC, datetime

from job_intake.models import (
    CanonicalJob,
    DescriptionBlock,
    JobClassification,
    RoleFamily,
    StudentFit,
)
from job_intake.notion.client import NotionPageRecord
from job_intake.notion.mapper import (
    NotionPageBlock,
    build_description_snippet,
    build_notion_job_page_blocks,
    build_notion_job_properties,
)
from job_intake.notion.sync import NotionSyncCandidate, NotionSyncService


class FakeSyncClient:
    def __init__(self) -> None:
        self.pages: dict[str, NotionPageRecord] = {}
        self.created_pages: list[dict[str, object | None]] = []
        self.created_blocks: list[tuple[object, ...]] = []
        self.updated_pages: list[tuple[str, dict[str, object | None], tuple[object, ...]]] = []
        self.find_calls = 0

    def find_page_by_canonical_job_key(
        self,
        *,
        database_id: str,
        canonical_job_key: str,
    ) -> NotionPageRecord | None:
        self.find_calls += 1
        return self.pages.get(canonical_job_key)

    def create_database_page(
        self,
        *,
        database_id: str,
        properties: dict[str, object | None],
        content_blocks: tuple[object, ...] | list[object],
    ) -> NotionPageRecord:
        page = NotionPageRecord(
            id=f"page-{len(self.pages) + 1}",
            properties=properties.copy(),
            managed_blocks=tuple(content_blocks),
        )
        self.pages[str(properties["Canonical Job Key"])] = page
        self.created_pages.append(properties.copy())
        self.created_blocks.append(tuple(content_blocks))
        return page

    def update_database_page(
        self,
        *,
        page_id: str,
        properties: dict[str, object | None],
        content_blocks: tuple[object, ...] | list[object],
    ) -> NotionPageRecord:
        canonical_job_key = str(properties["Canonical Job Key"])
        page = NotionPageRecord(
            id=page_id,
            properties=properties.copy(),
            managed_blocks=tuple(content_blocks),
        )
        self.pages[canonical_job_key] = page
        self.updated_pages.append((page_id, properties.copy(), tuple(content_blocks)))
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

    assert properties["Job URL"] == "https://www.linkedin.com/jobs/view/4185654374/"


def test_build_description_snippet_normalizes_whitespace_and_caps_length() -> None:
    snippet = build_description_snippet("Build   ETL\npipelines " * 50)

    assert snippet is not None
    assert "\n" not in snippet
    assert len(snippet) <= 453


def test_build_notion_job_page_blocks_returns_description_only() -> None:
    candidate = build_candidate()

    blocks = build_notion_job_page_blocks(candidate.job, candidate.classification)

    assert blocks == [
        NotionPageBlock(type="paragraph", text="Build ETL pipelines with Airflow."),
    ]


def test_build_notion_job_page_blocks_renders_structured_description_blocks() -> None:
    candidate = build_candidate()
    candidate.job = CanonicalJob(
        **{
            **candidate.job.model_dump(),
            "description_blocks": [
                DescriptionBlock(type="heading", text="Your tasks"),
                DescriptionBlock(type="bulleted_list_item", text="Build pipelines"),
                DescriptionBlock(type="numbered_list_item", text="Present updates"),
            ],
        }
    )

    blocks = build_notion_job_page_blocks(candidate.job, candidate.classification)

    assert blocks[0].type == "heading_3"
    assert blocks[0].text == "Your tasks"
    assert blocks[1].type == "bulleted_list_item"
    assert blocks[1].text == "Build pipelines"
    assert blocks[2].type == "numbered_list_item"
    assert blocks[2].text == "Present updates"


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
    assert client.find_calls == 2


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


def test_sync_candidate_with_page_hint_updates_without_lookup() -> None:
    client = FakeSyncClient()
    service = NotionSyncService(client, database_id="database-id")
    candidate = build_candidate(posted_text="today")

    result = service.sync_candidate_with_page_hint(
        candidate,
        existing_page_id="page-123",
    )

    assert result.action == "updated"
    assert result.page_id == "page-123"
    assert client.find_calls == 0
    assert client.updated_pages[0][0] == "page-123"


def test_sync_shortlisted_jobs_updates_existing_pages_when_only_page_body_changes() -> None:
    client = FakeSyncClient()
    service = NotionSyncService(client, database_id="database-id")
    long_description = ("Build ETL pipelines with SQL and Airflow. " * 20).strip()
    original = build_candidate()
    original.job = CanonicalJob(
        **{
            **original.job.model_dump(),
            "description_blocks": [
                DescriptionBlock(type="paragraph", text=long_description),
            ],
        }
    )
    changed = build_candidate()
    changed.job = CanonicalJob(
        **{
            **changed.job.model_dump(),
            "description_blocks": [
                DescriptionBlock(type="paragraph", text=long_description),
                DescriptionBlock(
                    type="paragraph",
                    text="This sentence only appears in the page body.",
                ),
            ],
        }
    )

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
