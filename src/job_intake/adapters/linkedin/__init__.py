"""LinkedIn adapter helpers for public job scraping."""

from job_intake.adapters.linkedin.fetch import (
    LinkedInFetchedPage,
    LinkedInFetchError,
    fetch_job_detail_page,
    fetch_search_results_page,
)
from job_intake.adapters.linkedin.models import LinkedInDiscoveryRecord, LinkedInJobDetail
from job_intake.adapters.linkedin.parser_detail import (
    extract_job_description_content,
    parse_job_detail_page,
)
from job_intake.adapters.linkedin.parser_list import parse_search_results_page

__all__ = [
    "LinkedInFetchedPage",
    "LinkedInFetchError",
    "LinkedInDiscoveryRecord",
    "LinkedInJobDetail",
    "extract_job_description_content",
    "fetch_job_detail_page",
    "fetch_search_results_page",
    "parse_job_detail_page",
    "parse_search_results_page",
]
