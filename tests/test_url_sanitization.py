from __future__ import annotations

from job_intake.canonical import normalize_linkedin_job_url


def test_normalize_linkedin_job_url_removes_embedded_ascii_whitespace() -> None:
    assert (
        normalize_linkedin_job_url(
            "https://www.linkedin.com/jobs/view/\n1234567890/\t?trk=public_jobs_topcard-title",
        )
        == "https://linkedin.com/jobs/view/1234567890"
    )
