"""Config-driven LinkedIn search definition execution helpers."""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlencode

from pydantic import BaseModel, Field

from job_intake.models import Platform, RoleFamily, SearchDefinition, SearchDefinitionsConfig

LINKEDIN_PUBLIC_SEARCH_URL = "https://www.linkedin.com/jobs/search/"


class ExecutableSearch(BaseModel):
    definition_name: str
    platform: Platform
    role_family: RoleFamily
    city: str
    keyword: str
    query_text: str
    filters: dict[str, str] = Field(default_factory=dict)
    search_url: str


def normalize_query_text(value: str) -> str:
    return " ".join(value.split())


def build_linkedin_search_url(
    *,
    keyword: str,
    city: str,
    filters: dict[str, str] | None = None,
) -> str:
    params: dict[str, str] = {
        "keywords": normalize_query_text(keyword),
        "location": normalize_query_text(city),
    }
    if filters:
        params.update(filters)
    return f"{LINKEDIN_PUBLIC_SEARCH_URL}?{urlencode(params)}"


def iter_executable_searches(
    definitions: Iterable[SearchDefinition],
) -> list[ExecutableSearch]:
    searches: list[ExecutableSearch] = []
    for definition in definitions:
        if not definition.enabled:
            continue

        for keyword in definition.keywords:
            normalized_keyword = normalize_query_text(keyword)
            searches.append(
                ExecutableSearch(
                    definition_name=definition.name,
                    platform=definition.platform,
                    role_family=definition.role_family,
                    city=definition.city,
                    keyword=normalized_keyword,
                    query_text=normalized_keyword,
                    filters=definition.filters,
                    search_url=build_linkedin_search_url(
                        keyword=normalized_keyword,
                        city=definition.city,
                        filters=definition.filters,
                    ),
                )
            )

    return searches


def build_executable_searches(config: SearchDefinitionsConfig) -> list[ExecutableSearch]:
    return iter_executable_searches(config.search_definitions)
