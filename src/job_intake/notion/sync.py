"""Notion sync interfaces for shortlisted jobs.

Supabase remains canonical. Notion is downstream and operational only.
Only shortlisted jobs should sync into the Notion review database, and manual workflow
fields must be preserved across updates.
"""

from __future__ import annotations

from collections.abc import Iterable

from job_intake.models import CanonicalJob


class NotionSyncService:
    """Placeholder for later Notion sync implementation.

    Expected guarantees for the eventual implementation:
    - Sync only shortlisted jobs, never the full raw corpus.
    - Preserve `Priority`, `Review Status`, `Application Status`, and `Notes`.
    - Use `Canonical Job Key` as the stable identity anchor.
    - Stay idempotent across reruns.
    """

    def sync_shortlisted_jobs(self, jobs: Iterable[CanonicalJob]) -> None:
        raise NotImplementedError(
            "Notion sync is intentionally not implemented in the foundation phase.",
        )

