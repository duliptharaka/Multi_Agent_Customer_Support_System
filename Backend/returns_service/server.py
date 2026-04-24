"""
Stand-alone A2A server for the Returns agent.

Run it from the ``Backend`` directory:

    python -m returns_service.server

or directly:

    python Backend\\returns_service\\server.py

It listens on http://localhost:8001 by default. The main customer-support
router consumes it via a ``RemoteA2aAgent`` pointed at
``http://localhost:8001/.well-known/agent-card.json``.

Override host/port with env vars:

    RETURNS_SERVICE_HOST   (default: 127.0.0.1)
    RETURNS_SERVICE_PORT   (default: 8001)
"""

from __future__ import annotations

import os

import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from .agent import returns_agent


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8001


def build_app(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    """Return the Starlette app that serves ``returns_agent`` over A2A.

    ``host`` / ``port`` are used to build the self-referencing agent-card
    URL, so they should match what uvicorn actually binds to.
    """
    return to_a2a(returns_agent, host=host, port=port)


def main() -> None:
    host = os.environ.get("RETURNS_SERVICE_HOST", DEFAULT_HOST)
    port = int(os.environ.get("RETURNS_SERVICE_PORT", DEFAULT_PORT))
    app = build_app(host=host, port=port)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
