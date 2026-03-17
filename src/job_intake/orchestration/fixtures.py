"""Shared fixture inputs for the local pipeline runners."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from job_intake.settings import Settings, get_settings


@dataclass(frozen=True, slots=True)
class FixturePipelineInputs:
    discovery_html_by_search_name: dict[str, str]
    detail_html_by_url: dict[str, str]


def _read_fixture(fixtures_dir: Path, name: str) -> str:
    return (fixtures_dir / name).read_text(encoding="utf-8")


def build_fixture_pipeline_inputs(
    settings: Settings | None = None,
) -> FixturePipelineInputs:
    active_settings = settings or get_settings()
    fixtures_dir = active_settings.repo_root / "tests" / "fixtures" / "linkedin"
    first_detail_url = (
        "https://www.linkedin.com/jobs/view/4185654374/"
        "?trk=public_jobs_jserp-result_search-card"
    )

    return FixturePipelineInputs(
        discovery_html_by_search_name={
            "berlin_data_engineering_student": _read_fixture(
                fixtures_dir,
                "list_search_results.html",
            ),
        },
        detail_html_by_url={
            first_detail_url: _read_fixture(fixtures_dir, "job_detail.html"),
            "https://www.linkedin.com/jobs/view/4185654375/": _read_fixture(
                fixtures_dir,
                "job_detail_missing_optional_fields.html",
            ),
        },
    )
