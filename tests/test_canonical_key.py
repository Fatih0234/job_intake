from __future__ import annotations

from job_intake.canonical import (
    build_canonical_job_key,
    extract_linkedin_external_job_id,
    normalize_linkedin_job_url,
)


def test_build_canonical_job_key_prefers_external_id() -> None:
    assert build_canonical_job_key(external_job_id="1234567890") == "linkedin:1234567890"


def test_build_canonical_job_key_uses_external_id_extracted_from_url() -> None:
    first = build_canonical_job_key(
        job_url="https://www.linkedin.com/jobs/view/1234567890/?trk=public_jobs_topcard-title",
    )
    second = build_canonical_job_key(job_url="https://linkedin.com/jobs/view/1234567890")

    assert first == second
    assert first == "linkedin:1234567890"


def test_build_canonical_job_key_falls_back_to_url_hash_when_id_is_missing() -> None:
    key = build_canonical_job_key(job_url="https://www.linkedin.com/jobs/collections/recommended/")

    assert key.startswith("linkedin:url:")


def test_normalize_linkedin_job_url_drops_tracking_query_and_www() -> None:
    assert (
        normalize_linkedin_job_url(
            "https://www.linkedin.com/jobs/view/1234567890/?trk=public_jobs_topcard-title",
        )
        == "https://linkedin.com/jobs/view/1234567890"
    )


def test_extract_linkedin_external_job_id_returns_none_when_missing() -> None:
    assert extract_linkedin_external_job_id("https://www.linkedin.com/jobs/search/") is None
