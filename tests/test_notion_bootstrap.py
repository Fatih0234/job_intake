from __future__ import annotations

from job_intake.notion.bootstrap import ensure_shortlist_workspace
from job_intake.notion.client import NotionDatabaseRef, NotionPageRef
from job_intake.notion.schema import MANUAL_FIELDS_TO_PRESERVE, required_database_properties
from job_intake.settings import Settings


class FakeNotionWorkspaceClient:
    def __init__(self) -> None:
        self.page: NotionPageRef | None = None
        self.database: NotionDatabaseRef | None = None
        self.created_pages: list[tuple[str, str | None]] = []
        self.created_databases: list[tuple[str, str, dict[str, str]]] = []

    def find_page_by_title(
        self,
        title: str,
        *,
        parent_page_id: str | None = None,
    ) -> NotionPageRef | None:
        if self.page and self.page.title == title:
            return self.page
        return None

    def create_page(self, title: str, *, parent_page_id: str | None = None) -> NotionPageRef:
        self.created_pages.append((title, parent_page_id))
        self.page = NotionPageRef(id="root-page-id", title=title)
        return self.page

    def find_database_by_title(
        self,
        title: str,
        *,
        parent_page_id: str | None = None,
    ) -> NotionDatabaseRef | None:
        if self.database and self.database.title == title:
            return self.database
        return None

    def create_database(
        self,
        *,
        parent_page_id: str,
        title: str,
        properties: dict[str, str],
    ) -> NotionDatabaseRef:
        self.created_databases.append((parent_page_id, title, properties))
        self.database = NotionDatabaseRef(
            id="database-id",
            title=title,
            properties=properties,
        )
        return self.database

    def get_database(self, database_id: str) -> NotionDatabaseRef:
        assert self.database is not None
        return self.database


def test_ensure_shortlist_workspace_creates_missing_root_page_and_database() -> None:
    client = FakeNotionWorkspaceClient()

    workspace = ensure_shortlist_workspace(client, Settings.from_overrides())

    assert workspace.created_root_page is True
    assert workspace.created_database is True
    assert client.created_pages == [("Student Job Intake", None)]
    assert client.created_databases[0][1] == "Student Jobs - Shortlist"
    assert client.created_databases[0][2] == required_database_properties()


def test_ensure_shortlist_workspace_reuses_existing_workspace() -> None:
    client = FakeNotionWorkspaceClient()
    client.page = NotionPageRef(id="root-page-id", title="Student Job Intake")
    client.database = NotionDatabaseRef(
        id="database-id",
        title="Student Jobs - Shortlist",
        properties=required_database_properties(),
    )

    workspace = ensure_shortlist_workspace(client, Settings.from_overrides())

    assert workspace.created_root_page is False
    assert workspace.created_database is False
    assert client.created_pages == []
    assert client.created_databases == []


def test_ensure_shortlist_workspace_rejects_database_with_missing_required_property() -> None:
    client = FakeNotionWorkspaceClient()
    client.page = NotionPageRef(id="root-page-id", title="Student Job Intake")
    client.database = NotionDatabaseRef(
        id="database-id",
        title="Student Jobs - Shortlist",
        properties={"Job Title": "title"},
    )

    try:
        ensure_shortlist_workspace(client, Settings.from_overrides())
    except ValueError as exc:
        assert "Company" in str(exc)
    else:
        raise AssertionError("Expected ensure_shortlist_workspace to reject missing properties.")


def test_manual_fields_to_preserve_match_schema_contract() -> None:
    assert set(MANUAL_FIELDS_TO_PRESERVE) == {
        "Priority",
        "Review Status",
        "Application Status",
        "Notes",
    }
