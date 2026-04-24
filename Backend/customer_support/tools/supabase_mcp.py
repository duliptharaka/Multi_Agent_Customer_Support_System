"""
Supabase MCP toolset factory.

Wraps the official Supabase MCP server (`@supabase/mcp-server-supabase`)
and exposes it as an ADK `MCPToolset` so any LlmAgent can call it.

Requires in the environment:
    SUPABASE_ACCESS_TOKEN   - personal access token (Supabase dashboard)
    SUPABASE_PROJECT_REF    - project ref, e.g. 'abcdxyz' (from the URL)

Also requires Node.js + npx on PATH (so `npx -y @supabase/mcp-server-supabase`
can start the server over stdio).
"""

from __future__ import annotations

import os
import re
from typing import Iterable, Optional
from urllib.parse import urlparse

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters


# Tools we actually want the agents to see. Limiting the surface keeps the
# model focused and prevents accidental schema-modifying calls.
DEFAULT_READONLY_TOOLS: tuple[str, ...] = (
    "list_tables",
    "list_extensions",
    "execute_sql",
)

_REF_PATTERN = re.compile(r"^[a-z0-9]{20,}$")


def _normalize_project_ref(value: str) -> str:
    """Accept either a raw project ref or a full Supabase URL.

    Supabase MCP needs the short ref (e.g. ``dqkmiuuawjxmmdljhkbw``), but
    users commonly paste the full URL (``https://<ref>.supabase.co``).
    Normalise transparently so the env var is forgiving.
    """
    value = value.strip().rstrip("/")
    if _REF_PATTERN.match(value):
        return value

    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = parsed.hostname or ""
    if host.endswith(".supabase.co"):
        return host.split(".", 1)[0]

    raise RuntimeError(
        f"Could not extract a Supabase project ref from {value!r}. "
        "Expected the short id (e.g. 'abcdxyz123...') or a URL like "
        "https://<project-ref>.supabase.co."
    )


def build_supabase_toolset(
    *,
    read_only: bool = True,
    tool_filter: Optional[Iterable[str]] = None,
) -> MCPToolset:
    """Return a configured Supabase MCP toolset.

    Args:
        read_only: Start the MCP server in --read-only mode. Strongly
            recommended for specialist agents that should only *query* data.
        tool_filter: Explicit allow-list of MCP tool names to expose. If
            None, ``DEFAULT_READONLY_TOOLS`` is used.
    """
    access_token = os.environ.get("SUPABASE_ACCESS_TOKEN")
    raw_project_ref = os.environ.get("SUPABASE_PROJECT_REF")

    if not access_token:
        raise RuntimeError(
            "SUPABASE_ACCESS_TOKEN is not set. Create a personal access token "
            "in the Supabase dashboard (Account -> Access Tokens) and add it "
            "to the root-level .env."
        )
    if not raw_project_ref:
        raise RuntimeError(
            "SUPABASE_PROJECT_REF is not set. Put either the short id or the "
            "full https://<project-ref>.supabase.co URL in the root-level .env."
        )

    project_ref = _normalize_project_ref(raw_project_ref)

    args = [
        "-y",
        "@supabase/mcp-server-supabase@latest",
        f"--project-ref={project_ref}",
    ]
    if read_only:
        args.append("--read-only")

    return MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=args,
                env={"SUPABASE_ACCESS_TOKEN": access_token},
            ),
            # npx pulls the MCP server on first launch - give it room to breathe.
            timeout=30.0,
        ),
        tool_filter=list(tool_filter) if tool_filter else list(DEFAULT_READONLY_TOOLS),
    )
