"""Canonical job key and LinkedIn URL normalization helpers."""

from __future__ import annotations

import re
from hashlib import sha256
from urllib.parse import urlsplit, urlunsplit

LINKEDIN_JOB_ID_RE = re.compile(r"/jobs/view/(?:[^/?#]*-)?(?P<job_id>\d+)")


def normalize_linkedin_job_url(job_url: str) -> str:
    cleaned = job_url.strip()
    parsed = urlsplit(cleaned)

    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")

    return urlunsplit((scheme, netloc, path, "", ""))


def extract_linkedin_external_job_id(job_url: str) -> str | None:
    match = LINKEDIN_JOB_ID_RE.search(normalize_linkedin_job_url(job_url))
    if not match:
        return None
    return match.group("job_id")


def build_canonical_job_key(
    *,
    external_job_id: str | None = None,
    job_url: str | None = None,
) -> str:
    if external_job_id:
        return f"linkedin:{external_job_id.strip()}"
    if not job_url:
        raise ValueError("Either external_job_id or job_url is required to build a canonical key.")

    external_job_id = extract_linkedin_external_job_id(job_url)
    if external_job_id:
        return f"linkedin:{external_job_id}"

    normalized = normalize_linkedin_job_url(job_url)
    digest = sha256(normalized.encode("utf-8")).hexdigest()[:20]
    return f"linkedin:url:{digest}"
