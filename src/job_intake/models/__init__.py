"""Typed domain models for the job intake pipeline foundation."""

from job_intake.models.common import Platform, RoleFamily, StudentFit
from job_intake.models.config import (
    LoadedConfigs,
    RoleFamilyKeywordRules,
    SearchDefinitionsConfig,
    StudentFitKeywordRules,
)
from job_intake.models.core import (
    CanonicalJob,
    JobClassification,
    JobDiscovery,
    SearchDefinition,
)

__all__ = [
    "CanonicalJob",
    "JobClassification",
    "JobDiscovery",
    "LoadedConfigs",
    "Platform",
    "RoleFamily",
    "RoleFamilyKeywordRules",
    "SearchDefinition",
    "SearchDefinitionsConfig",
    "StudentFit",
    "StudentFitKeywordRules",
]
