"""Bootstrap helpers for the Notion review workspace."""

from __future__ import annotations

from dataclasses import dataclass

from job_intake.notion.client import NotionDatabaseRef, NotionPageRef, NotionWorkspaceClient
from job_intake.notion.schema import (
    DEFAULT_DATABASE_NAME,
    DEFAULT_ROOT_PAGE_NAME,
    missing_required_database_properties,
    required_database_properties,
)
from job_intake.settings import Settings, get_settings


@dataclass(slots=True)
class NotionWorkspaceState:
    root_page: NotionPageRef
    database: NotionDatabaseRef
    created_root_page: bool
    created_database: bool


def ensure_shortlist_workspace(
    client: NotionWorkspaceClient,
    settings: Settings | None = None,
) -> NotionWorkspaceState:
    active_settings = settings or get_settings()

    root_page, created_root_page = _resolve_root_page(client, active_settings)
    database, created_database = _resolve_database(client, active_settings, root_page.id)
    missing_properties = missing_required_database_properties(database.properties)
    if missing_properties:
        missing = ", ".join(missing_properties)
        raise ValueError(f"Notion database is missing required properties: {missing}")

    return NotionWorkspaceState(
        root_page=root_page,
        database=database,
        created_root_page=created_root_page,
        created_database=created_database,
    )


def _resolve_root_page(
    client: NotionWorkspaceClient,
    settings: Settings,
) -> tuple[NotionPageRef, bool]:
    if settings.notion.root_page_id:
        existing_root_page = client.find_page_by_title(
            settings.notion.default_root_page_name,
            parent_page_id=settings.notion.parent_page_id,
        )
        if existing_root_page:
            return existing_root_page, False

        root_page = NotionPageRef(
            id=settings.notion.root_page_id,
            title=settings.notion.default_root_page_name,
        )
        return root_page, False

    existing_root_page = client.find_page_by_title(
        settings.notion.default_root_page_name,
        parent_page_id=settings.notion.parent_page_id,
    )
    if existing_root_page:
        return existing_root_page, False

    return client.create_page(
        settings.notion.default_root_page_name,
        parent_page_id=settings.notion.parent_page_id,
    ), True


def _resolve_database(
    client: NotionWorkspaceClient,
    settings: Settings,
    root_page_id: str,
) -> tuple[NotionDatabaseRef, bool]:
    if settings.notion.database_id:
        return client.get_database(settings.notion.database_id), False

    database = client.find_database_by_title(
        settings.notion.default_database_name,
        parent_page_id=root_page_id,
    )
    if database:
        return database, False

    return client.create_database(
        parent_page_id=root_page_id,
        title=settings.notion.default_database_name,
        properties=required_database_properties(),
    ), True


__all__ = [
    "DEFAULT_DATABASE_NAME",
    "DEFAULT_ROOT_PAGE_NAME",
    "NotionWorkspaceState",
    "ensure_shortlist_workspace",
]
