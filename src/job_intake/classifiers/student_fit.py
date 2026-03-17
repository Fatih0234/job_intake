"""Deterministic student-fit classification rules."""

from __future__ import annotations

from pydantic import BaseModel, Field

from job_intake.classifiers.keyword_rules import find_term_matches
from job_intake.models import CanonicalJob, StudentFit, StudentFitKeywordRules


class StudentFitDecision(BaseModel):
    student_fit: StudentFit
    signals: dict[str, list[str]] = Field(default_factory=dict)
    reason: str


def classify_student_fit(
    job: CanonicalJob,
    keyword_rules: StudentFitKeywordRules,
) -> StudentFitDecision:
    title_matches = find_term_matches(job.title, keyword_rules.positive_terms)
    description_matches = find_term_matches(
        job.description_text or "",
        keyword_rules.positive_terms,
    )
    employment_matches = find_term_matches(job.employment_type or "", keyword_rules.positive_terms)
    supporting_matches = find_term_matches(
        " ".join(filter(None, [job.title, job.description_text, job.employment_type])),
        keyword_rules.supporting_terms,
    )
    negative_matches = find_term_matches(
        " ".join(filter(None, [job.title, job.description_text, job.seniority])),
        keyword_rules.negative_terms,
    )

    positive_matches = sorted(set(title_matches + description_matches + employment_matches))
    signals = {
        "positive_terms": positive_matches,
        "supporting_terms": supporting_matches,
        "negative_terms": negative_matches,
    }

    if title_matches or employment_matches:
        if negative_matches and not positive_matches:
            return StudentFitDecision(
                student_fit=StudentFit.NOT_STUDENT_JOB,
                signals=signals,
                reason="negative seniority signals without student indicators",
            )
        return StudentFitDecision(
            student_fit=StudentFit.TARGET_STUDENT_JOB,
            signals=signals,
            reason="strong student indicators in title or employment type",
        )

    if positive_matches and not negative_matches:
        return StudentFitDecision(
            student_fit=StudentFit.TARGET_STUDENT_JOB,
            signals=signals,
            reason="student indicators present in the description",
        )

    if supporting_matches and not negative_matches:
        return StudentFitDecision(
            student_fit=StudentFit.POSSIBLE_STUDENT_JOB,
            signals=signals,
            reason="supporting student indicators without strong title signals",
        )

    return StudentFitDecision(
        student_fit=StudentFit.NOT_STUDENT_JOB,
        signals=signals,
        reason="insufficient student indicators",
    )
