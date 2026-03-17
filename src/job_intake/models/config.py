"""Typed repository configuration models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from job_intake.models.common import Platform, RoleFamily
from job_intake.models.core import SearchDefinition


def _clean_terms(values: list[str], *, field_name: str) -> list[str]:
    cleaned = [value.strip() for value in values if value.strip()]
    if not cleaned:
        raise ValueError(f"{field_name} must contain at least one non-empty value.")
    return cleaned


class SearchDefinitionsConfig(BaseModel):
    target_cities: list[str] = Field(default_factory=list)
    search_definitions: list[SearchDefinition] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_definitions(self) -> SearchDefinitionsConfig:
        target_cities = {city.strip() for city in self.target_cities if city.strip()}
        if not target_cities:
            raise ValueError("target_cities must contain at least one city.")

        seen_names: set[str] = set()
        for definition in self.search_definitions:
            if definition.name in seen_names:
                raise ValueError(f"Duplicate search definition name {definition.name!r}.")
            seen_names.add(definition.name)

            if definition.platform is not Platform.LINKEDIN:
                raise ValueError("Only LinkedIn search definitions are allowed in v1.")
            if definition.city not in target_cities:
                raise ValueError(
                    f"Search definition {definition.name!r} uses non-target city "
                    f"{definition.city!r}.",
                )

        return self


class StudentFitKeywordRules(BaseModel):
    positive_terms: list[str] = Field(default_factory=list)
    supporting_terms: list[str] = Field(default_factory=list)
    negative_terms: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_terms(self) -> StudentFitKeywordRules:
        self.positive_terms = _clean_terms(self.positive_terms, field_name="positive_terms")
        self.negative_terms = _clean_terms(self.negative_terms, field_name="negative_terms")
        self.supporting_terms = [value.strip() for value in self.supporting_terms if value.strip()]
        return self


class RoleKeywordSet(BaseModel):
    keywords: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_keywords(self) -> RoleKeywordSet:
        self.keywords = _clean_terms(self.keywords, field_name="keywords")
        return self


class RoleFamilyKeywordRules(BaseModel):
    role_families: dict[RoleFamily, RoleKeywordSet] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_role_families(self) -> RoleFamilyKeywordRules:
        required_role_families = {
            RoleFamily.DATA_ENGINEERING,
            RoleFamily.ANALYTICS_ENGINEERING,
            RoleFamily.ANALYTICS_BI,
            RoleFamily.ML_AI_ENGINEERING,
        }

        configured_role_families = set(self.role_families)
        missing = required_role_families - configured_role_families
        if missing:
            missing_labels = ", ".join(sorted(role_family.value for role_family in missing))
            raise ValueError(f"Missing keyword rules for role families: {missing_labels}.")
        if RoleFamily.OUT_OF_SCOPE in configured_role_families:
            raise ValueError("out_of_scope must not be configured as a keyword-driven role family.")

        return self


class LoadedConfigs(BaseModel):
    linkedin_searches: SearchDefinitionsConfig
    student_fit_keywords: StudentFitKeywordRules
    role_family_keywords: RoleFamilyKeywordRules

    def as_dict(self) -> dict[str, dict[str, Any]]:
        return {
            "linkedin_searches.yaml": self.linkedin_searches.model_dump(mode="json"),
            "student_fit_keywords.yaml": self.student_fit_keywords.model_dump(mode="json"),
            "role_family_keywords.yaml": self.role_family_keywords.model_dump(mode="json"),
        }
