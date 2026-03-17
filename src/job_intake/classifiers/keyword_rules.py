"""Shared deterministic text matching helpers for classifier modules."""

from __future__ import annotations

import re


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    lowered = value.casefold()
    return re.sub(r"\s+", " ", lowered).strip()


def find_term_matches(text: str, terms: list[str]) -> list[str]:
    normalized_text = normalize_text(text)
    matches: list[str] = []
    for term in terms:
        normalized_term = normalize_text(term)
        if normalized_term and normalized_term in normalized_text:
            matches.append(term)
    return matches
