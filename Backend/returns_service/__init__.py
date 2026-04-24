"""
Returns A2A Service.

Runs as a **separate** process from the main customer-support agents.
Exposes a single ``returns_agent`` with two tools
(``check_return_eligibility``, ``initiate_return``) over the
Agent-to-Agent (A2A) protocol so the main router can consume it as a
remote sub-agent.

Env vars are sourced from the repo-root ``.env`` the same way the main
package does it, so both processes share one config file.
"""

from pathlib import Path

from dotenv import load_dotenv

# <repo-root>/Backend/returns_service/__init__.py  ->  parents[2] = repo-root
_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ROOT_ENV, override=False)
