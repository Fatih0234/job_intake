from __future__ import annotations

from pathlib import Path
from uuid import UUID

from job_intake.adapters.linkedin import LinkedInFetchedPage
from job_intake.models import JobDiscovery, PipelineRun, SearchDefinition
from job_intake.orchestration import LinkedInLiveDiscoveryRunner
from job_intake.settings import Settings

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "linkedin"


class FakeLiveDiscoveryRepository:
    def __init__(self) -> None:
        self.discovery_records: list[tuple[JobDiscovery, UUID | None, UUID | None]] = []
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

    def upsert_search_definition(self, definition: SearchDefinition) -> UUID:
        return UUID("00000000-0000-4000-8000-000000000002")

    def insert_job_discovery(
        self,
        discovery: JobDiscovery,
        *,
        pipeline_run_id: UUID | None = None,
        job_id: UUID | None = None,
    ) -> UUID:
        self.discovery_records.append((discovery, pipeline_run_id, job_id))
        return UUID("00000000-0000-4000-8000-000000000003")


def read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def test_live_discovery_runner_persists_discoveries_from_live_fetch_html() -> None:
    repository = FakeLiveDiscoveryRepository()
    runner = LinkedInLiveDiscoveryRunner(
        repository,
        fetcher=lambda search_url: LinkedInFetchedPage(
            requested_url=search_url,
            final_url=search_url,
            status_code=200,
            html=read_fixture("list_search_results.html"),
        ),
    )

    summary = runner.run(settings=Settings.from_overrides(), limit_searches=1)

    assert summary.searches_attempted == 1
    assert summary.searches_succeeded == 1
    assert summary.searches_failed == 0
    assert summary.discoveries_inserted == 2
    assert summary.errors == []
    assert len(repository.discovery_records) == 2
    assert all(
        record[0].search_definition_id == UUID("00000000-0000-4000-8000-000000000002")
        for record in repository.discovery_records
    )
    assert repository.pipeline_updates[-1]["status"] == "succeeded"


def test_live_discovery_runner_records_fetch_errors_without_crashing_run() -> None:
    repository = FakeLiveDiscoveryRepository()

    def raising_fetcher(search_url: str) -> LinkedInFetchedPage:
        raise RuntimeError(f"fetch failed for {search_url}")

    runner = LinkedInLiveDiscoveryRunner(repository, fetcher=raising_fetcher)

    summary = runner.run(settings=Settings.from_overrides(), limit_searches=1)

    assert summary.searches_attempted == 1
    assert summary.searches_succeeded == 0
    assert summary.searches_failed == 1
    assert summary.discoveries_inserted == 0
    assert len(summary.errors) == 1
    assert "fetch failed" in summary.errors[0]
    assert repository.pipeline_updates[-1]["status"] == "completed_with_errors"
