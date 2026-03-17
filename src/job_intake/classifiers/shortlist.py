"""Shortlist and sync eligibility decisions."""

from __future__ import annotations

from pydantic import BaseModel, Field

from job_intake.models import CanonicalJob, RoleFamily, StudentFit


class ShortlistDecision(BaseModel):
    shortlist_decision: bool
    shortlist_reason: str
    signals: dict[str, object] = Field(default_factory=dict)


def decide_shortlist(
    job: CanonicalJob,
    *,
    student_fit: StudentFit,
    role_family: RoleFamily,
    target_cities: list[str],
) -> ShortlistDecision:
    in_scope_city = job.city in set(target_cities)
    in_scope_role_family = role_family is not RoleFamily.OUT_OF_SCOPE
    has_required_fields = bool(job.title and job.description_text)
    is_student_fit = student_fit in {
        StudentFit.TARGET_STUDENT_JOB,
        StudentFit.POSSIBLE_STUDENT_JOB,
    }

    shortlist_decision = all(
        [in_scope_city, in_scope_role_family, has_required_fields, is_student_fit]
    )
    sync_candidate = shortlist_decision and student_fit is StudentFit.TARGET_STUDENT_JOB

    reasons: list[str] = []
    if in_scope_city:
        reasons.append("city in scope")
    else:
        reasons.append("city out of scope")
    if in_scope_role_family:
        reasons.append("role family in scope")
    else:
        reasons.append("role family out of scope")
    if has_required_fields:
        reasons.append("required fields present")
    else:
        reasons.append("missing required fields")
    if is_student_fit:
        reasons.append("student fit eligible")
    else:
        reasons.append("student fit not eligible")

    return ShortlistDecision(
        shortlist_decision=shortlist_decision,
        shortlist_reason="; ".join(reasons),
        signals={
            "city_in_scope": in_scope_city,
            "role_family_in_scope": in_scope_role_family,
            "required_fields_present": has_required_fields,
            "sync_candidate": sync_candidate,
        },
    )
