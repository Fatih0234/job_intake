"""Parser for LinkedIn public job detail pages."""

from __future__ import annotations

import json
import re
from html import unescape
from typing import Any

from job_intake.adapters.linkedin.models import LinkedInJobDetail, parse_iso_datetime

CLASS_ATTR_RE = re.compile(r'class="[^"]*\b{class_name}\b[^"]*"')
ATTR_RE_TEMPLATE = r'{attribute}="(?P<value>[^"]+)"'
JOB_ID_RE = re.compile(r"/jobs/view/(?:[^/?#]*-)?(?P<job_id>\d+)")
CRITERIA_ITEM_RE = re.compile(
    r"<li\b[^>]*class=\"[^\"]*description__job-criteria-item[^\"]*\"[^>]*>(?P<item>.*?)</li>",
    re.IGNORECASE | re.DOTALL,
)
JSON_LD_RE = re.compile(
    r"<script\b[^>]*type=[\"']application/ld\+json[\"'][^>]*>(?P<json>.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)

CRITERIA_LABEL_MAP = {
    "employment type": "employment_type",
    "beschäftigungsverhältnis": "employment_type",
    "seniority level": "seniority",
    "karrierestufe": "seniority",
    "job function": "job_function",
    "tätigkeitsbereich": "job_function",
    "taetigkeitsbereich": "job_function",
    "industries": "industries",
    "branchen": "industries",
}


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


def _extract_metadata_attr(
    block: str,
    *,
    tag: str,
    attribute_filters: dict[str, str],
    target_attribute: str,
) -> str | None:
    filter_pattern = "".join(
        rf'(?=[^>]*{re.escape(attribute)}="{re.escape(value)}")'
        for attribute, value in attribute_filters.items()
    )
    pattern = re.compile(
        rf"<{tag}\b{filter_pattern}[^>]*{ATTR_RE_TEMPLATE.format(attribute=re.escape(target_attribute))}[^>]*>",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(block)
    return unescape(match.group("value")).strip() if match else None


def _extract_job_posting_jsonld(block: str) -> dict[str, Any]:
    for match in JSON_LD_RE.finditer(block):
        try:
            payload = json.loads(match.group("json"))
        except json.JSONDecodeError:
            continue

        candidates = payload if isinstance(payload, list) else [payload]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            candidate_type = candidate.get("@type")
            if candidate_type == "JobPosting" or (
                isinstance(candidate_type, list) and "JobPosting" in candidate_type
            ):
                return candidate

    return {}


def _extract_jsonld_company(job_posting: dict[str, Any]) -> str | None:
    organization = job_posting.get("hiringOrganization")
    if isinstance(organization, dict):
        name = organization.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def _extract_jsonld_location(job_posting: dict[str, Any]) -> str | None:
    job_location = job_posting.get("jobLocation")
    locations = job_location if isinstance(job_location, list) else [job_location]
    for location in locations:
        if not isinstance(location, dict):
            continue
        address = location.get("address")
        if not isinstance(address, dict):
            continue
        locality = str(address.get("addressLocality") or "").strip()
        region = str(address.get("addressRegion") or "").strip()
        country = str(address.get("addressCountry") or "").strip()
        parts = [locality, region]
        if country and (len(country) > 2 or not locality):
            parts.append(country)
        normalized = ", ".join(part for part in parts if part)
        if normalized:
            return normalized
    return None


def _extract_jsonld_description(job_posting: dict[str, Any]) -> str | None:
    description = job_posting.get("description")
    if not isinstance(description, str) or not description.strip():
        return None
    return _strip_tags(unescape(description))


def _extract_criteria(block: str) -> dict[str, str]:
    criteria: dict[str, str] = {}
    for match in CRITERIA_ITEM_RE.finditer(block):
        item = match.group("item")
        heading = _extract_text(item, class_name="description__job-criteria-subheader", tag="h3")
        value = _extract_text(item, class_name="description__job-criteria-text", tag="span")
        if heading and value:
            normalized_heading = CRITERIA_LABEL_MAP.get(heading.lower().strip())
            if normalized_heading:
                criteria[normalized_heading] = value
    return criteria


def _split_industries(value: str | None) -> list[str]:
    if not value:
        return []
    return [
        part.strip()
        for part in re.split(r"\s*(?:,|\bund\b|\band\b)\s*", value, flags=re.IGNORECASE)
        if part.strip()
    ]


def parse_job_detail_page(html: str, *, source_search_name: str | None = None) -> LinkedInJobDetail:
    job_posting = _extract_job_posting_jsonld(html)
    job_url = _extract_attr(html, class_name="topcard__link", attribute="href") or _extract_attr(
        html,
        class_name="topcard__content-left",
        attribute="data-job-url",
    )
    if not job_url:
        job_url = _extract_metadata_attr(
            html,
            tag="link",
            attribute_filters={"rel": "canonical"},
            target_attribute="href",
        ) or _extract_metadata_attr(
            html,
            tag="meta",
            attribute_filters={"property": "og:url"},
            target_attribute="content",
        ) or _extract_metadata_attr(
            html,
            tag="meta",
            attribute_filters={"property": "lnkd:url"},
            target_attribute="content",
        )

    title = _extract_text(html, class_name="topcard__title", tag="h1")
    if not title:
        job_posting_title = job_posting.get("title")
        if isinstance(job_posting_title, str) and job_posting_title.strip():
            title = job_posting_title.strip()

    company = _extract_text(html, class_name="topcard__org-name-link", tag="a")
    if not company:
        company = _extract_text(html, class_name="topcard__flavor", tag="span")
    if not company:
        company = _extract_jsonld_company(job_posting)

    location_raw = _extract_text(html, class_name="topcard__flavor--bullet", tag="span")
    if not location_raw:
        location_raw = _extract_jsonld_location(job_posting)

    posted_text = _extract_text(html, class_name="posted-time-ago__text", tag="span")
    description_text = _extract_text(html, class_name="show-more-less-html__markup", tag="div")
    if not description_text:
        description_text = _extract_jsonld_description(job_posting)

    posted_datetime = _extract_attr(html, class_name="posted-time-ago__text", attribute="datetime")
    if not posted_datetime:
        jsonld_posted_datetime = job_posting.get("datePosted")
        if isinstance(jsonld_posted_datetime, str) and jsonld_posted_datetime.strip():
            posted_datetime = jsonld_posted_datetime.strip()

    criteria = _extract_criteria(html)

    if not job_url or not title or not company:
        raise ValueError("LinkedIn detail page is missing one of: job_url, title, company.")

    external_job_id_match = JOB_ID_RE.search(job_url)
    industries = _split_industries(criteria.get("industries"))

    return LinkedInJobDetail(
        external_job_id=external_job_id_match.group("job_id") if external_job_id_match else None,
        job_url=job_url,
        title=title,
        company=company,
        location_raw=location_raw,
        description_text=description_text,
        employment_type=criteria.get("employment_type"),
        seniority=criteria.get("seniority"),
        job_function=criteria.get("job_function"),
        industries=industries,
        posted_text=posted_text,
        posted_at=parse_iso_datetime(posted_datetime),
        source_search_name=source_search_name,
        raw_payload={"detail_html": html},
    )
