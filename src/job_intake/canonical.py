"""Canonical job key and LinkedIn URL normalization helpers."""

from __future__ import annotations

from hashlib import sha256
from urllib.parse import urlsplit, urlunsplit


def normalize_linkedin_job_url(job_url: str) -> str:
    cleaned = job_url.strip()
    parsed = urlsplit(cleaned)

    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")

    return urlunsplit((scheme, netloc, path, "", ""))


def build_canonical_job_key(
    *,
    external_job_id: str | None = None,
    job_url: str | None = None,
) -> str:
    if external_job_id:
        return f"linkedin:{external_job_id.strip()}"
    if not job_url:
        raise ValueError("Either external_job_id or job_url is required to build a canonical key.")

    normalized = normalize_linkedin_job_url(job_url)
    digest = sha256(normalized.encode("utf-8")).hexdigest()[:20]
    return f"linkedin:url:{digest}"
