#!/usr/bin/env python3
"""Validate the local setup and print the next actions."""

from __future__ import annotations

from pprint import pprint

from job_intake.config_loader import load_all_configs
from job_intake.settings import get_settings


def main() -> int:
    settings = get_settings()
    configs = load_all_configs(settings)
    missing = settings.missing_local_values()

    print("Student Job Intake local bootstrap")
    print("=" * 36)
    print(f"Environment: {settings.app.env}")
    print(f"Configs loaded: {', '.join(sorted(configs.keys()))}")
    print()

    print("Missing local values")
    pprint(missing)
    print()

    print("Next steps")
    print("- Copy .env.local.example to .env.local if you have not done that yet.")
    print("- Fill SUPABASE_DB_URL before using storage helpers or running DB-backed checks.")
    print("- Run: supabase link --project-ref aashdnhoiqqdhpdedaab")
    print("- If the remote schema may have changed later, run: supabase db pull")
    print("- Prefer Notion MCP for workspace bootstrap; use NOTION_API_TOKEN only as fallback.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

