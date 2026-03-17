"""LinkedIn adapter helpers for public job scraping."""

from job_intake.adapters.linkedin.models import LinkedInDiscoveryRecord
from job_intake.adapters.linkedin.parser_list import parse_search_results_page

__all__ = ["LinkedInDiscoveryRecord", "parse_search_results_page"]
