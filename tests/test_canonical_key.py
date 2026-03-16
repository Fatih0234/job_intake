from __future__ import annotations

from job_intake.canonical import build_canonical_job_key, normalize_linkedin_job_url


def test_build_canonical_job_key_prefers_external_id() -> None:
    assert build_canonical_job_key(external_job_id="1234567890") == "linkedin:1234567890"


def test_build_canonical_job_key_fallback_is_deterministic_across_url_variants() -> None:
    first = build_canonical_job_key(
        job_url="https://www.linkedin.com/jobs/view/1234567890/?trk=public_jobs_topcard-title",
    )
    second = build_canonical_job_key(job_url="https://linkedin.com/jobs/view/1234567890")

    assert first == second
    assert first.startswith("linkedin:url:")


def test_normalize_linkedin_job_url_drops_tracking_query_and_www() -> None:
    assert (
        normalize_linkedin_job_url(
            "https://www.linkedin.com/jobs/view/1234567890/?trk=public_jobs_topcard-title",
        )
        == "https://linkedin.com/jobs/view/1234567890"
    )

