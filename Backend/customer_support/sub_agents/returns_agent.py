"""
Thin ``RemoteA2aAgent`` proxy that points the main router at the
standalone Returns A2A service (``Backend/returns_service``).

The URL is configurable via the ``RETURNS_AGENT_URL`` env var so the
router can talk to the service whether it's running locally, in Docker,
or on another host.
"""

from __future__ import annotations

import os

from google.adk.agents.remote_a2a_agent import (
    AGENT_CARD_WELL_KNOWN_PATH,
    RemoteA2aAgent,
)


DEFAULT_RETURNS_SERVICE_URL = "http://127.0.0.1:8001"


def _agent_card_url() -> str:
    base = os.environ.get("RETURNS_AGENT_URL", DEFAULT_RETURNS_SERVICE_URL)
    return base.rstrip("/") + AGENT_CARD_WELL_KNOWN_PATH


returns_agent = RemoteA2aAgent(
    name="returns_agent",
    description=(
        "Remote specialist (A2A) that checks an order's return eligibility "
        "and initiates the return when the customer confirms. Runs as a "
        "separate process; see Backend/returns_service."
    ),
    agent_card=_agent_card_url(),
)
