"""Fallback direct Notion client wrapper.

Preferred control plane: Notion MCP.
This module exists only so future sync code has a small fallback wrapper when MCP is
unavailable or insufficient.
"""

from __future__ import annotations

from notion_client import Client

from job_intake.settings import Settings, get_settings


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

