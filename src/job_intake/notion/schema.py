"""Notion schema placeholders for the downstream shortlist workspace."""

DEFAULT_ROOT_PAGE_NAME = "Student Job Intake"
DEFAULT_DATABASE_NAME = "Student Jobs - Shortlist"

REQUIRED_DATABASE_PROPERTIES = {
    "Job Title": "title",
    "Company": "rich_text",
    "City": "rich_text",
    "Platform": "select",
    "Role Family": "select",
    "Student Fit": "select",
    "Posted Text": "rich_text",
    "Job URL": "url",
    "Shortlist Reason": "rich_text",
    "Priority": "select",
    "Review Status": "status",
    "Application Status": "status",
    "Notes": "rich_text",
    "Source Search Name": "rich_text",
    "Canonical Job Key": "rich_text",
    "Synced At": "date",
    "Last Seen At": "date",
}

MANUAL_FIELDS_TO_PRESERVE = (
    "Priority",
    "Review Status",
    "Application Status",
    "Notes",
)

