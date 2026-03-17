"""Notion workspace client abstractions and direct-API fallback wrapper."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, cast

from notion_client import Client

from job_intake.notion.mapper import NotionPageBlock
from job_intake.notion.schema import DATABASE_PROPERTY_SPECS
from job_intake.settings import Settings, get_settings

RICH_TEXT_CHUNK_SIZE = 1800


@dataclass(slots=True)
class NotionPageRef:
    id: str
    title: str


@dataclass(slots=True)
class NotionDatabaseRef:
    id: str
    title: str
    properties: dict[str, str]


@dataclass(slots=True)
class NotionPageRecord:
    id: str
    properties: dict[str, object | None]
    managed_blocks: tuple[NotionPageBlock, ...] = ()


class NotionBootstrapClient(Protocol):
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
    def update_database(
        self,
        *,
        database_id: str,
        properties: dict[str, str],
    ) -> NotionDatabaseRef: ...
    def get_database(self, database_id: str) -> NotionDatabaseRef: ...


class NotionSyncClient(Protocol):
    def find_page_by_canonical_job_key(
        self,
        *,
        database_id: str,
        canonical_job_key: str,
    ) -> NotionPageRecord | None: ...
    def create_database_page(
        self,
        *,
        database_id: str,
        properties: dict[str, object | None],
        content_blocks: Sequence[NotionPageBlock],
    ) -> NotionPageRecord: ...
    def update_database_page(
        self,
        *,
        page_id: str,
        properties: dict[str, object | None],
        content_blocks: Sequence[NotionPageBlock],
    ) -> NotionPageRecord: ...


class NotionWorkspaceClient(NotionBootstrapClient, NotionSyncClient, Protocol):
    pass


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
        self._data_source_ids_by_database_id: dict[str, str] = {}

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

    def update_database(
        self,
        *,
        database_id: str,
        properties: dict[str, str],
    ) -> NotionDatabaseRef:
        existing_database = self.get_database(database_id)
        properties_to_add = {
            property_name: {property_type: {}}
            for property_name, property_type in properties.items()
            if existing_database.properties.get(property_name) != property_type
        }
        if not properties_to_add:
            return existing_database

        response = cast(
            dict[str, Any],
            self.client.databases.update(
                database_id=database_id,
                properties=properties_to_add,
            ),
        )
        return NotionDatabaseRef(
            id=response["id"],
            title=self._extract_title(response),
            properties=self._extract_database_properties(response),
        )

    def find_page_by_canonical_job_key(
        self,
        *,
        database_id: str,
        canonical_job_key: str,
    ) -> NotionPageRecord | None:
        data_source_id = self._resolve_data_source_id(database_id)
        response = cast(
            dict[str, Any],
            cast(Any, self.client.data_sources).query(
                data_source_id=data_source_id,
                filter={
                    "property": "Canonical Job Key",
                    "rich_text": {"equals": canonical_job_key},
                },
            ),
        )
        results = response.get("results", [])
        if not results:
            return None
        page = cast(dict[str, Any], results[0])
        return self._to_page_record(
            page,
            managed_blocks=self._extract_managed_blocks(page["id"]),
        )

    def create_database_page(
        self,
        *,
        database_id: str,
        properties: dict[str, object | None],
        content_blocks: Sequence[NotionPageBlock],
    ) -> NotionPageRecord:
        page_create_payload: dict[str, Any] = {
            "parent": {"database_id": database_id},
            "properties": self._build_property_payload(properties),
        }
        if content_blocks:
            page_create_payload["children"] = self._build_block_payload(content_blocks)
        response = cast(
            dict[str, Any],
            self.client.pages.create(**page_create_payload),
        )
        return self._to_page_record(response, managed_blocks=tuple(content_blocks))

    def update_database_page(
        self,
        *,
        page_id: str,
        properties: dict[str, object | None],
        content_blocks: Sequence[NotionPageBlock],
    ) -> NotionPageRecord:
        response = cast(
            dict[str, Any],
            self.client.pages.update(
                page_id=page_id,
                properties=self._build_property_payload(properties),
            ),
        )
        self._replace_page_content(
            page_id=page_id,
            managed_blocks=tuple(content_blocks),
        )
        return self._to_page_record(response, managed_blocks=tuple(content_blocks))

    def _extract_title(self, response: dict[str, Any]) -> str:
        title_fragments = response.get("title", [])
        return "".join(fragment.get("plain_text", "") for fragment in title_fragments)

    def _extract_database_properties(self, response: dict[str, Any]) -> dict[str, str]:
        return {
            property_name: property_payload["type"]
            for property_name, property_payload in response.get("properties", {}).items()
        }

    def _to_page_record(
        self,
        response: dict[str, Any],
        *,
        managed_blocks: tuple[NotionPageBlock, ...] = (),
    ) -> NotionPageRecord:
        return NotionPageRecord(
            id=response["id"],
            properties={
                property_name: self._from_notion_property_value(property_payload)
                for property_name, property_payload in response.get("properties", {}).items()
            },
            managed_blocks=managed_blocks,
        )

    def _resolve_data_source_id(self, database_id: str) -> str:
        cached_id = self._data_source_ids_by_database_id.get(database_id)
        if cached_id:
            return cached_id

        response = cast(
            dict[str, Any],
            self.client.databases.retrieve(database_id=database_id),
        )
        data_sources = cast(list[dict[str, Any]], response.get("data_sources", []))
        if not data_sources:
            raise RuntimeError(f"Database {database_id} does not expose any data sources.")

        data_source_id = str(data_sources[0]["id"])
        self._data_source_ids_by_database_id[database_id] = data_source_id
        return data_source_id

    def _build_property_payload(
        self,
        properties: dict[str, object | None],
    ) -> dict[str, dict[str, Any]]:
        payload: dict[str, dict[str, Any]] = {}
        for property_name, property_value in properties.items():
            property_type = DATABASE_PROPERTY_SPECS[property_name].type
            payload[property_name] = self._to_notion_property_value(property_type, property_value)
        return payload

    def _to_notion_property_value(
        self,
        property_type: str,
        value: object | None,
    ) -> dict[str, Any]:
        if property_type == "title":
            return {
                "title": (
                    []
                    if value is None
                    else [{"type": "text", "text": {"content": str(value)}}]
                )
            }
        if property_type == "rich_text":
            return {
                "rich_text": (
                    []
                    if value is None
                    else [{"type": "text", "text": {"content": str(value)}}]
                )
            }
        if property_type == "url":
            return {"url": None if value is None else str(value)}
        if property_type in {"select", "status"}:
            return {property_type: None if value is None else {"name": str(value)}}
        if property_type == "date":
            if value is None:
                return {"date": None}
            if isinstance(value, datetime):
                return {"date": {"start": value.isoformat()}}
            return {"date": {"start": str(value)}}
        raise ValueError(f"Unsupported Notion property type {property_type!r}.")

    def _build_block_payload(
        self,
        blocks: Sequence[NotionPageBlock],
    ) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for block in blocks:
            payload.append(
                {
                    "object": "block",
                    "type": block.type,
                    block.type: {
                        "rich_text": self._build_rich_text(block.text),
                    },
                }
            )
        return payload

    def _build_rich_text(self, text: str) -> list[dict[str, Any]]:
        if not text:
            return []
        return [
            {
                "type": "text",
                "text": {"content": text[start : start + RICH_TEXT_CHUNK_SIZE]},
            }
            for start in range(0, len(text), RICH_TEXT_CHUNK_SIZE)
        ]

    def _extract_managed_blocks(self, page_id: str) -> tuple[NotionPageBlock, ...]:
        blocks = self._list_block_children(page_id)
        managed_blocks: list[NotionPageBlock] = []
        for block in blocks:
            page_block = self._to_page_block(block)
            if page_block is not None:
                managed_blocks.append(page_block)
        return tuple(managed_blocks)

    def _to_page_block(self, block: dict[str, Any]) -> NotionPageBlock | None:
        block_type = block["type"]
        if block_type not in {
            "heading_2",
            "heading_3",
            "paragraph",
            "bulleted_list_item",
            "numbered_list_item",
        }:
            return None
        return NotionPageBlock(
            type=block_type,
            text=self._extract_block_text(block),
        )

    def _replace_page_content(
        self,
        *,
        page_id: str,
        managed_blocks: tuple[NotionPageBlock, ...],
    ) -> None:
        existing_blocks = self._list_block_children(page_id)
        new_blocks = self._build_block_payload(managed_blocks)
        self._delete_blocks(existing_blocks)
        if new_blocks:
            self._append_blocks(page_id, new_blocks)

    def _list_block_children(self, block_id: str) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        next_cursor: str | None = None

        while True:
            response = cast(
                dict[str, Any],
                self.client.blocks.children.list(
                    block_id=block_id,
                    start_cursor=next_cursor,
                ),
            )
            blocks.extend(cast(list[dict[str, Any]], response.get("results", [])))
            if not response.get("has_more"):
                break
            next_cursor = cast(str, response.get("next_cursor"))

        return blocks

    def _extract_block_text(self, block: dict[str, Any]) -> str:
        block_type = block["type"]
        payload = block.get(block_type, {})
        return "".join(
            fragment.get("plain_text", "")
            for fragment in payload.get("rich_text", [])
        )

    def _delete_blocks(self, blocks: Sequence[dict[str, Any]]) -> None:
        for block in blocks:
            cast(Any, self.client.blocks).delete(block_id=block["id"])

    def _append_blocks(
        self,
        page_id: str,
        blocks: Sequence[dict[str, Any]],
    ) -> None:
        for start in range(0, len(blocks), 50):
            cast(Any, self.client.blocks.children).append(
                block_id=page_id,
                children=list(blocks[start : start + 50]),
            )

    def _from_notion_property_value(self, property_payload: dict[str, Any]) -> object | None:
        property_type = property_payload["type"]
        if property_type == "title":
            return "".join(fragment.get("plain_text", "") for fragment in property_payload["title"])
        if property_type == "rich_text":
            return "".join(
                fragment.get("plain_text", "")
                for fragment in property_payload["rich_text"]
            )
        if property_type == "url":
            return property_payload["url"]
        if property_type in {"select", "status"}:
            selected = property_payload[property_type]
            return None if selected is None else selected.get("name")
        if property_type == "date":
            date_value = property_payload["date"]
            return None if date_value is None else date_value.get("start")
        return None
