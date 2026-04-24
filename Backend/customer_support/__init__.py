"""Multi-Agent Customer Support System (ADK package).

The single source of truth for environment variables is the **root-level**
``.env`` at the repo root (two directories above this file). It is loaded
here so it is in place before any sub-module (config, tools, sub-agents)
reads ``os.environ``.

Layout::

    <repo-root>/
        .env                        <-- loaded here
        Backend/
            customer_support/
                __init__.py         <-- this file
                agent.py
                ...
"""

from pathlib import Path

from dotenv import load_dotenv

# Resolve <repo-root>/.env regardless of where Python is launched from.
_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ROOT_ENV, override=False)

from . import agent  # noqa: E402  (must come *after* load_dotenv)

__all__ = ["agent"]
