"""Notion workspace client abstractions and direct-API fallback wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, cast

from notion_client import Client

from job_intake.settings import Settings, get_settings


@dataclass(slots=True)
class NotionPageRef:
    id: str
    title: str


@dataclass(slots=True)
class NotionDatabaseRef:
    id: str
    title: str
    properties: dict[str, str]


class NotionWorkspaceClient(Protocol):
    def find_page_by_title(
        self,
        title: str,
        *,
        parent_page_id: str | None = None,
    ) -> NotionPageRef | None: ...
    def create_page(
        self,
        title: str,
        *,
        parent_page_id: str | None = None,
    ) -> NotionPageRef: ...
    def find_database_by_title(
        self,
        title: str,
        *,
        parent_page_id: str | None = None,
    ) -> NotionDatabaseRef | None: ...
    def create_database(
        self,
        *,
        parent_page_id: str,
        title: str,
        properties: dict[str, str],
    ) -> NotionDatabaseRef: ...
    def get_database(self, database_id: str) -> NotionDatabaseRef: ...


class NotionFallbackClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.notion.api_token)

    def build(self) -> Client:
        if not self.settings.notion.api_token:
            raise RuntimeError(
                "NOTION_API_TOKEN is required only when using the direct Notion API fallback.",
            )
        return Client(auth=self.settings.notion.api_token)

    def workspace_client(self) -> NotionWorkspaceClient:
        return DirectNotionWorkspaceClient(self.build())


class DirectNotionWorkspaceClient:
    def __init__(self, client: Client) -> None:
        self.client = client

    def find_page_by_title(
        self,
        title: str,
        *,
        parent_page_id: str | None = None,
    ) -> NotionPageRef | None:
        response = cast(
            dict[str, Any],
            self.client.search(
                query=title,
                filter={"property": "object", "value": "page"},
            ),
        )
        for result in response["results"]:
            if result["object"] != "page":
                continue
            if self._extract_title(result) != title:
                continue
            if parent_page_id and result.get("parent", {}).get("page_id") != parent_page_id:
                continue
            return NotionPageRef(id=result["id"], title=title)
        return None

    def create_page(self, title: str, *, parent_page_id: str | None = None) -> NotionPageRef:
        if parent_page_id:
            parent: dict[str, Any] = {"type": "page_id", "page_id": parent_page_id}
        else:
            parent = {"type": "workspace", "workspace": True}

        response = cast(
            dict[str, Any],
            self.client.pages.create(
                parent=parent,
                properties={
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": title},
                        }
                    ]
                },
            ),
        )
        return NotionPageRef(id=response["id"], title=title)

    def find_database_by_title(
        self,
        title: str,
        *,
        parent_page_id: str | None = None,
    ) -> NotionDatabaseRef | None:
        response = cast(
            dict[str, Any],
            self.client.search(
                query=title,
                filter={"property": "object", "value": "database"},
            ),
        )
        for result in response["results"]:
            if result["object"] != "database":
                continue
            if self._extract_title(result) != title:
                continue
            if parent_page_id and result.get("parent", {}).get("page_id") != parent_page_id:
                continue
            return self.get_database(result["id"])
        return None

    def create_database(
        self,
        *,
        parent_page_id: str,
        title: str,
        properties: dict[str, str],
    ) -> NotionDatabaseRef:
        notion_properties: dict[str, dict[str, Any]] = {
            property_name: {property_type: {}}
            for property_name, property_type in properties.items()
        }
        response = cast(
            dict[str, Any],
            self.client.databases.create(
                parent={"type": "page_id", "page_id": parent_page_id},
                title=[
                    {
                        "type": "text",
                        "text": {"content": title},
                    }
                ],
                properties=notion_properties,
            ),
        )
        return NotionDatabaseRef(
            id=response["id"],
            title=title,
            properties=self._extract_database_properties(response),
        )

    def get_database(self, database_id: str) -> NotionDatabaseRef:
        response = cast(
            dict[str, Any],
            self.client.databases.retrieve(database_id=database_id),
        )
        return NotionDatabaseRef(
            id=response["id"],
            title=self._extract_title(response),
            properties=self._extract_database_properties(response),
        )

    def _extract_title(self, response: dict[str, Any]) -> str:
        title_fragments = response.get("title", [])
        return "".join(fragment.get("plain_text", "") for fragment in title_fragments)

    def _extract_database_properties(self, response: dict[str, Any]) -> dict[str, str]:
        return {
            property_name: property_payload["type"]
            for property_name, property_payload in response.get("properties", {}).items()
        }
