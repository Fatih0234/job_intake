"""LinkedIn adapter helpers for public job scraping."""

from job_intake.adapters.linkedin.models import LinkedInDiscoveryRecord, LinkedInJobDetail
from job_intake.adapters.linkedin.parser_detail import parse_job_detail_page
from job_intake.adapters.linkedin.parser_list import parse_search_results_page

__all__ = [
    "LinkedInDiscoveryRecord",
    "LinkedInJobDetail",
    "parse_job_detail_page",
    "parse_search_results_page",
]
