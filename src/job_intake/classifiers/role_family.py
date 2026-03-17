"""Deterministic role-family classification rules."""

from __future__ import annotations

from pydantic import BaseModel, Field

from job_intake.classifiers.keyword_rules import find_term_matches
from job_intake.models import CanonicalJob, RoleFamily, RoleFamilyKeywordRules


class RoleFamilyDecision(BaseModel):
    role_family: RoleFamily
    scores: dict[str, int] = Field(default_factory=dict)
    matched_terms: dict[str, list[str]] = Field(default_factory=dict)
    reason: str


def classify_role_family(
    job: CanonicalJob,
    keyword_rules: RoleFamilyKeywordRules,
) -> RoleFamilyDecision:
    scores: dict[str, int] = {}
    matched_terms: dict[str, list[str]] = {}

    for role_family, rule_set in keyword_rules.role_families.items():
        title_matches = find_term_matches(job.title, rule_set.keywords)
        description_matches = find_term_matches(job.description_text or "", rule_set.keywords)
        score = (len(title_matches) * 3) + len(description_matches)
        scores[role_family.value] = score
        matched_terms[role_family.value] = sorted(set(title_matches + description_matches))

    best_role_family, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score <= 0:
        return RoleFamilyDecision(
            role_family=RoleFamily.OUT_OF_SCOPE,
            scores=scores,
            matched_terms=matched_terms,
            reason="no role-family keywords matched",
        )

    return RoleFamilyDecision(
        role_family=RoleFamily(best_role_family),
        scores=scores,
        matched_terms=matched_terms,
        reason=f"highest weighted keyword score for {best_role_family}",
    )
