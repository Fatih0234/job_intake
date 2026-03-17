from __future__ import annotations

from job_intake.orchestration import build_fixture_pipeline_inputs
from job_intake.settings import Settings


def test_build_fixture_pipeline_inputs_returns_expected_fixture_slice() -> None:
    fixture_inputs = build_fixture_pipeline_inputs(Settings.from_overrides())

    assert list(fixture_inputs.discovery_html_by_search_name) == [
        "berlin_data_engineering_student",
    ]
    assert set(fixture_inputs.detail_html_by_url) == {
        "https://www.linkedin.com/jobs/view/4185654375/",
        "https://www.linkedin.com/jobs/view/4185654374/?trk=public_jobs_jserp-result_search-card",
    }
    assert "Data Engineering Working Student" in fixture_inputs.detail_html_by_url[
        "https://www.linkedin.com/jobs/view/4185654374/?trk=public_jobs_jserp-result_search-card"
    ]
