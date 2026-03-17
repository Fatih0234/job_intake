from __future__ import annotations

from job_intake.config_loader import load_search_definitions_config
from job_intake.models import Platform, RoleFamily, SearchDefinition, SearchDefinitionsConfig
from job_intake.search_definitions import (
    build_executable_searches,
    build_linkedin_search_url,
    normalize_query_text,
)
from job_intake.settings import Settings


def test_normalize_query_text_collapses_whitespace() -> None:
    assert (
        normalize_query_text("  working   student   data engineer  ")
        == "working student data engineer"
    )


def test_build_linkedin_search_url_includes_location_keyword_and_filters() -> None:
    search_url = build_linkedin_search_url(
        keyword="Werkstudent Data Engineering",
        city="Berlin",
        filters={"f_TPR": "r604800"},
    )

    assert "keywords=Werkstudent+Data+Engineering" in search_url
    assert "location=Berlin" in search_url
    assert "f_TPR=r604800" in search_url


def test_build_executable_searches_skips_disabled_definitions() -> None:
    config = SearchDefinitionsConfig(
        target_cities=["Berlin"],
        search_definitions=[
            SearchDefinition(
                name="enabled",
                city="Berlin",
                role_family=RoleFamily.DATA_ENGINEERING,
                keywords=["Werkstudent Data Engineering"],
                enabled=True,
            ),
            SearchDefinition(
                name="disabled",
                city="Berlin",
                role_family=RoleFamily.DATA_ENGINEERING,
                keywords=["working student data engineer"],
                enabled=False,
            ),
        ],
    )

    searches = build_executable_searches(config)

    assert len(searches) == 1
    assert searches[0].definition_name == "enabled"
    assert searches[0].platform is Platform.LINKEDIN


def test_build_executable_searches_expands_repository_config() -> None:
    config = load_search_definitions_config(Settings())

    searches = build_executable_searches(config)

    assert len(searches) == 15
    assert searches[0].city == "Berlin"
    assert searches[0].search_url.startswith("https://www.linkedin.com/jobs/search/?")
