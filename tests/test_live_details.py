from __future__ import annotations

from pathlib import Path
from uuid import UUID

from job_intake.adapters.linkedin import LinkedInFetchedPage
from job_intake.models import CanonicalJob, JobDiscovery, PipelineRun
from job_intake.orchestration import LinkedInLiveDetailsRunner

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "linkedin"


class FakeLiveDetailsRepository:
    def __init__(self, discoveries: list[JobDiscovery]) -> None:
        self.discoveries = discoveries
        self.jobs: list[CanonicalJob] = []
        self.links: list[tuple[UUID, UUID]] = []
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

    def list_latest_unlinked_job_discoveries(self, *, limit: int) -> list[JobDiscovery]:
        return self.discoveries[:limit]

    def upsert_job(self, job: CanonicalJob) -> UUID:
        self.jobs.append(job)
        return UUID("00000000-0000-4000-8000-000000000010")

    def update_job_discovery_job_link(
        self,
        *,
        discovery_id: UUID,
        job_id: UUID,
    ) -> None:
        self.links.append((discovery_id, job_id))


def read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def test_live_details_runner_fetches_parses_and_links_jobs() -> None:
    discovery = JobDiscovery(
        id=UUID("00000000-0000-4000-8000-000000000100"),
        external_job_id="4185654374",
        discovery_url=(
            "https://www.linkedin.com/jobs/view/4185654374/"
            "?trk=public_jobs_jserp-result_search-card"
        ),
        raw_payload={"source_search_name": "berlin_data_engineering_student"},
    )
    repository = FakeLiveDetailsRepository([discovery])
    runner = LinkedInLiveDetailsRunner(
        repository,
        fetcher=lambda job_url: LinkedInFetchedPage(
            requested_url=job_url,
            final_url=job_url,
            status_code=200,
            html=read_fixture("job_detail.html"),
        ),
    )

    summary = runner.run(limit_discoveries=1)

    assert summary.discoveries_attempted == 1
    assert summary.details_succeeded == 1
    assert summary.details_failed == 0
    assert summary.jobs_upserted == 1
    assert summary.discoveries_linked == 1
    assert summary.errors == []
    assert repository.jobs[0].canonical_job_key == "linkedin:4185654374"
    assert repository.links == [
        (
            UUID("00000000-0000-4000-8000-000000000100"),
            UUID("00000000-0000-4000-8000-000000000010"),
        )
    ]
    assert repository.pipeline_updates[-1]["status"] == "succeeded"


def test_live_details_runner_records_errors_and_continues() -> None:
    first = JobDiscovery(
        id=UUID("00000000-0000-4000-8000-000000000101"),
        external_job_id="4185654374",
        discovery_url="https://www.linkedin.com/jobs/view/4185654374/",
        raw_payload={"source_search_name": "berlin_data_engineering_student"},
    )
    second = JobDiscovery(
        id=UUID("00000000-0000-4000-8000-000000000102"),
        external_job_id="4185654375",
        discovery_url="https://www.linkedin.com/jobs/view/4185654375/",
        raw_payload={"source_search_name": "berlin_data_engineering_student"},
    )
    repository = FakeLiveDetailsRepository([first, second])

    def fetcher(job_url: str) -> LinkedInFetchedPage:
        if job_url.endswith("4185654374/"):
            raise RuntimeError("detail fetch failed")
        return LinkedInFetchedPage(
            requested_url=job_url,
            final_url=job_url,
            status_code=200,
            html=read_fixture("job_detail_missing_optional_fields.html"),
        )

    runner = LinkedInLiveDetailsRunner(repository, fetcher=fetcher)

    summary = runner.run(limit_discoveries=2)

    assert summary.discoveries_attempted == 2
    assert summary.details_succeeded == 1
    assert summary.details_failed == 1
    assert summary.jobs_upserted == 1
    assert summary.discoveries_linked == 1
    assert len(summary.errors) == 1
    assert "detail fetch failed" in summary.errors[0]
    assert repository.pipeline_updates[-1]["status"] == "completed_with_errors"


def test_live_details_runner_handles_live_public_guest_detail_shape() -> None:
    discovery = JobDiscovery(
        id=UUID("00000000-0000-4000-8000-000000000103"),
        external_job_id="4382858518",
        discovery_url=(
            "https://de.linkedin.com/jobs/view/"
            "werkstudent-data-engineering-bei-acme-analytics-4382858518"
        ),
        raw_payload={"source_search_name": "berlin_data_engineering_student"},
    )
    repository = FakeLiveDetailsRepository([discovery])
    runner = LinkedInLiveDetailsRunner(
        repository,
        fetcher=lambda job_url: LinkedInFetchedPage(
            requested_url=job_url,
            final_url=job_url,
            status_code=200,
            html=read_fixture("job_detail_live_public_de.html"),
        ),
    )

    summary = runner.run(limit_discoveries=1)

    assert summary.details_succeeded == 1
    assert summary.details_failed == 0
    assert repository.jobs[0].canonical_job_key == "linkedin:4382858518"
    assert repository.jobs[0].employment_type == "Teilzeit"
    assert repository.jobs[0].city == "Berlin"


def test_live_details_runner_sleeps_between_discoveries_only() -> None:
    first = JobDiscovery(
        id=UUID("00000000-0000-4000-8000-000000000104"),
        external_job_id="4185654374",
        discovery_url="https://www.linkedin.com/jobs/view/4185654374/",
        raw_payload={"source_search_name": "berlin_data_engineering_student"},
    )
    second = JobDiscovery(
        id=UUID("00000000-0000-4000-8000-000000000105"),
        external_job_id="4185654375",
        discovery_url="https://www.linkedin.com/jobs/view/4185654375/",
        raw_payload={"source_search_name": "berlin_data_engineering_student"},
    )
    sleep_calls: list[float] = []
    repository = FakeLiveDetailsRepository([first, second])
    runner = LinkedInLiveDetailsRunner(
        repository,
        fetcher=lambda job_url: LinkedInFetchedPage(
            requested_url=job_url,
            final_url=job_url,
            status_code=200,
            html=read_fixture("job_detail.html"),
        ),
        sleeper=sleep_calls.append,
    )

    summary = runner.run(limit_discoveries=2, request_delay_seconds=0.75)

    assert summary.details_succeeded == 2
    assert sleep_calls == [0.75]
