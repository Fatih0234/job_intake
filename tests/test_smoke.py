from __future__ import annotations

from job_intake.config_loader import load_all_configs
from job_intake.settings import Settings
from job_intake.smoke import run_smoke_check


def test_all_yaml_configs_parse() -> None:
    configs = load_all_configs(Settings())

    assert len(configs.linkedin_searches.search_definitions) == 5
    assert "Werkstudent" in configs.student_fit_keywords.positive_terms
    assert configs.role_family_keywords.role_families


def test_smoke_check_runs_without_db_credentials() -> None:
    result = run_smoke_check(Settings())

    assert result["settings_loaded"] is True
    assert result["search_definition_count"] == 5
    assert result["executable_search_count"] == 15
    assert result["sample_search_url"].startswith("https://www.linkedin.com/jobs/search/?")
    assert result["sample_external_key"] == "linkedin:1234567890"
    assert result["sample_fallback_key"].startswith("linkedin:url:")
    assert result["pipeline_summary"]["discoveries"] == 2
    assert result["pipeline_summary"]["shortlisted"] == 2
    assert result["pipeline_summary"]["errors"] == []
