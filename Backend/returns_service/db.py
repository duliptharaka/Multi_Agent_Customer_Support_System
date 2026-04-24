"""
Thin Supabase SQL helper for the Returns service.

We intentionally avoid spinning up *another* ``npx @supabase/mcp-server``
here: the existing customer-support agents already use MCP in read-only
mode, and the Returns flow needs **writes** (creating tickets, updating
order status). Instead we hit Supabase's Management API SQL endpoint
directly:

    POST https://api.supabase.com/v1/projects/{ref}/database/query
    Authorization: Bearer <SUPABASE_ACCESS_TOKEN>
    Body: { "query": "<sql>" }

This is the same endpoint Supabase MCP uses under the hood, so it works
with the personal access token we already have.
"""

from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import urlparse

import httpx

_REF_PATTERN = re.compile(r"^[a-z0-9]{20,}$")
_MGMT_URL = "https://api.supabase.com/v1/projects/{ref}/database/query"


def _normalize_project_ref(value: str) -> str:
    """Accept either a raw project ref or a full Supabase URL."""
    value = value.strip().rstrip("/")
    if _REF_PATTERN.match(value):
        return value
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = parsed.hostname or ""
    if host.endswith(".supabase.co"):
        return host.split(".", 1)[0]
    raise RuntimeError(f"Invalid SUPABASE_PROJECT_REF: {value!r}")


def quote_literal(value: Any) -> str:
    """Postgres-safe SQL literal for a Python value.

    Tiny on purpose - covers the (int, str) cases the Returns tools need.
    Strings are single-quoted with embedded quotes doubled. Integers are
    rendered directly.
    """
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def execute_sql(query: str) -> list[dict[str, Any]]:
    """Run a SQL statement against the project and return rows as dicts."""
    access_token = os.environ.get("SUPABASE_ACCESS_TOKEN")
    project_ref = os.environ.get("SUPABASE_PROJECT_REF")
    if not access_token or not project_ref:
        raise RuntimeError(
            "SUPABASE_ACCESS_TOKEN and SUPABASE_PROJECT_REF must be set in .env"
        )
    url = _MGMT_URL.format(ref=_normalize_project_ref(project_ref))
    response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        json={"query": query},
        timeout=30.0,
    )
    response.raise_for_status()
    payload = response.json()
    # Supabase returns either a list of row dicts, or an object with a
    # ``result`` key depending on the statement. Normalise to list.
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if "result" in payload and isinstance(payload["result"], list):
            return payload["result"]
        return [payload]
    return []
