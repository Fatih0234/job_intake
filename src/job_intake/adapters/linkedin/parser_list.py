"""Parser for LinkedIn public job search result pages."""

from __future__ import annotations

import re
from html import unescape

from job_intake.adapters.linkedin.models import LinkedInDiscoveryRecord, parse_iso_datetime

CARD_BLOCK_RE = re.compile(r"<li\b[^>]*>(?P<card>.*?)</li>", re.IGNORECASE | re.DOTALL)
CLASS_ATTR_RE = re.compile(r'class="[^"]*\b{class_name}\b[^"]*"')
TAG_TEXT_RE = r"<{tag}\b[^>]*>(?P<value>.*?)</{tag}>"
ATTR_RE_TEMPLATE = r'{attribute}="(?P<value>[^"]+)"'
JOB_ID_RE = re.compile(r"/jobs/view/(?P<job_id>\d+)")


def _strip_tags(value: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", value)).split())


def _extract_attr(block: str, *, class_name: str, attribute: str) -> str | None:
    pattern = re.compile(
        rf"<(?P<tag>\w+)\b[^>]*{CLASS_ATTR_RE.pattern.format(class_name=re.escape(class_name))}"
        rf'[^>]*{ATTR_RE_TEMPLATE.format(attribute=re.escape(attribute))}[^>]*>',
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(block)
    return unescape(match.group("value")).strip() if match else None


def _extract_text(block: str, *, class_name: str, tag: str) -> str | None:
    pattern = re.compile(
        rf"<{tag}\b[^>]*{CLASS_ATTR_RE.pattern.format(class_name=re.escape(class_name))}[^>]*>"
        rf"(?P<value>.*?)</{tag}>",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(block)
    if not match:
        return None
    cleaned = _strip_tags(match.group("value"))
    return cleaned or None


def _extract_company(block: str) -> str | None:
    company = _extract_text(block, class_name="base-search-card__subtitle", tag="h4")
    if company:
        return company
    return _extract_text(block, class_name="hidden-nested-link", tag="a")


def parse_search_results_page(
    html: str,
    *,
    source_search_name: str,
) -> list[LinkedInDiscoveryRecord]:
    discoveries: list[LinkedInDiscoveryRecord] = []

    for card_index, match in enumerate(CARD_BLOCK_RE.finditer(html), start=1):
        card = match.group("card")
        if "base-search-card" not in card:
            continue

        job_url = _extract_attr(card, class_name="base-card__full-link", attribute="href")
        title = _extract_text(card, class_name="base-search-card__title", tag="h3")
        company = _extract_company(card)
        location_raw = _extract_text(card, class_name="job-search-card__location", tag="span")
        posted_text = _extract_text(card, class_name="job-search-card__listdate", tag="time")
        posted_datetime = _extract_attr(
            card,
            class_name="job-search-card__listdate",
            attribute="datetime",
        )

        if not job_url or not title or not company:
            continue

        external_job_id_match = JOB_ID_RE.search(job_url)
        discoveries.append(
            LinkedInDiscoveryRecord(
                external_job_id=(
                    external_job_id_match.group("job_id")
                    if external_job_id_match
                    else None
                ),
                title=title,
                company=company,
                location_raw=location_raw,
                job_url=job_url,
                posted_text=posted_text,
                posted_at=parse_iso_datetime(posted_datetime),
                rank_position=card_index,
                source_search_name=source_search_name,
                raw_payload={"card_html": card},
            )
        )

    return discoveries
