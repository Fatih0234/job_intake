from __future__ import annotations

from pathlib import Path

import pytest

from job_intake.adapters.linkedin import parse_job_detail_page

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "linkedin"


def read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def test_parse_job_detail_page_extracts_normalized_detail() -> None:
    detail = parse_job_detail_page(
        read_fixture("job_detail.html"),
        source_search_name="berlin_data_engineering_student",
    )

    canonical_job = detail.to_canonical_job()

    assert detail.external_job_id == "4185654374"
    assert detail.employment_type == "Part-time"
    assert detail.seniority == "Internship"
    assert detail.industries == ["Software Development", "Data Infrastructure"]
    assert canonical_job.canonical_job_key == "linkedin:4185654374"
    assert canonical_job.city == "Berlin"
    assert canonical_job.metadata["job_function"] == "Engineering and Information Technology"


def test_parse_job_detail_page_handles_missing_optional_fields_explicitly() -> None:
    detail = parse_job_detail_page(read_fixture("job_detail_missing_optional_fields.html"))

    canonical_job = detail.to_canonical_job()

    assert detail.posted_text is None
    assert detail.seniority is None
    assert detail.job_function is None
    assert detail.industries == []
    assert canonical_job.canonical_job_key == "linkedin:4185654375"


def test_parse_job_detail_page_raises_when_required_fields_are_missing() -> None:
    with pytest.raises(ValueError, match="missing one of"):
        parse_job_detail_page("<html><body><h1 class=\"topcard__title\">Broken</h1></body></html>")
