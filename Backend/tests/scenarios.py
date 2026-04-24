"""
End-to-end scenarios for the Multi-Agent Customer Support System.

Exercises the whole stack in three live conversations:

    1. Billing (MCP)       -> router delegates to ticket_agent, which runs
                              SELECTs against Supabase via the read-only MCP
                              toolset.
    2. Returns (A2A)       -> router delegates to the returns_agent
                              (RemoteA2aAgent), which in turn calls the
                              FunctionTools on the separate returns_service
                              via the A2A protocol.
    3. Escalation          -> returns_agent politely refuses an out-of-window
                              return, the user asks to escalate, and control
                              returns to the router, which hands off to
                              ticket_agent for manual triage.

Run::

    C:\\Users\\dmadura\\.venvs\\cs-agents\\Scripts\\python.exe -m tests.scenarios

(from the ``Backend`` directory). The script starts / stops the Returns A2A
service automatically so there's no second-terminal dance.

Side effects
------------
Scenario 2 is a *real* return: it inserts a new row into ``support_tickets``
and flips ``orders.status`` to ``returned``. Re-run the schema.sql from
``Backend/database`` to reset between runs if you want a clean slate.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

# Quiet the ambient noise from ADK (experimental feature banners), authlib,
# and LiteLLM's "Provider List:" info line so the scenario output is readable.
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger("LiteLLM").setLevel(logging.ERROR)
import litellm  # noqa: E402

litellm.suppress_debug_info = True

import httpx  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

# Trigger .env loading + build the router.
from customer_support.agent import root_agent  # noqa: E402


APP_NAME = "customer_support"
USER_ID = "demo_user"

RETURNS_SERVICE_URL = os.environ.get(
    "RETURNS_AGENT_URL", "http://127.0.0.1:8001"
).rstrip("/")
RETURNS_CARD_URL = f"{RETURNS_SERVICE_URL}/.well-known/agent-card.json"


# --------------------------------------------------------------------- #
# Scenarios                                                             #
# --------------------------------------------------------------------- #

@dataclass
class Scenario:
    title: str
    session_id: str
    turns: Sequence[str]
    intent: str


SCENARIOS: list[Scenario] = [
    Scenario(
        title="Billing (MCP)",
        session_id="s1_billing",
        intent=(
            "Router should delegate to ticket_agent, which then uses the "
            "Supabase MCP tools (execute_sql) to look up the customer and "
            "their billing ticket."
        ),
        turns=[
            "Hi - I was charged for order #8 even though I cancelled it "
            "last week. My email is henry.walker@example.com. Can you "
            "check my open tickets about this?",
        ],
    ),
    Scenario(
        title="Returns (A2A)",
        session_id="s2_returns",
        intent=(
            "Router should delegate to returns_agent (RemoteA2aAgent). "
            "Over A2A, the remote returns_agent calls "
            "check_return_eligibility and then initiate_return."
        ),
        turns=[
            "Hello, I'd like to return order #7 - the Bluetooth speaker "
            "battery lasts about 2 hours instead of the 10 hours you "
            "advertised. My email is grace.chen@example.com.",
            "Yes, please go ahead and initiate the return.",
        ],
    ),
    Scenario(
        title="Escalation (A2A rejects -> ticket_agent triage)",
        session_id="s3_escalation",
        intent=(
            "Order #4 is 45 days old, so returns_agent will reject it. "
            "When the user asks to escalate, control must flow back to "
            "the router, which should delegate to ticket_agent for a "
            "triage summary."
        ),
        turns=[
            "I'd like to return order #4 - the 'E' key on my mechanical "
            "keyboard sticks after only a couple weeks. My email is "
            "david.lee@example.com.",
            "I understand the 30-day window has closed, but this is "
            "clearly a manufacturing defect. Please escalate this to a "
            "human agent so someone can review it.",
        ],
    ),
]


# --------------------------------------------------------------------- #
# Pretty printer                                                        #
# --------------------------------------------------------------------- #

BAR = "=" * 76
SUB = "-" * 76


def _truncate(value: object, limit: int = 360) -> str:
    text = repr(value) if not isinstance(value, str) else value
    return text if len(text) <= limit else text[:limit] + "  …"


def _render_event(event) -> None:
    author = event.author or "?"
    if not event.content or not event.content.parts:
        return

    for part in event.content.parts:
        if getattr(part, "text", None):
            text = (part.text or "").strip()
            if text:
                print(f"  [{author}] {text}")
            continue

        fc = getattr(part, "function_call", None)
        if fc is not None:
            args = _truncate(dict(fc.args) if fc.args else {})
            print(f"  [{author} -> tool] {fc.name}({args})")
            continue

        fr = getattr(part, "function_response", None)
        if fr is not None:
            resp = _truncate(fr.response)
            print(f"  [{author} <- tool] {fr.name} -> {resp}")
            continue


# --------------------------------------------------------------------- #
# A2A service lifecycle                                                 #
# --------------------------------------------------------------------- #

def _backend_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def start_returns_service() -> subprocess.Popen | None:
    """Start the Returns A2A server unless one is already healthy."""
    try:
        httpx.get(RETURNS_CARD_URL, timeout=1.5).raise_for_status()
        print(f"[harness] Returns A2A already running at {RETURNS_SERVICE_URL}")
        return None
    except (httpx.HTTPError, httpx.ConnectError, OSError):
        pass

    print(f"[harness] Launching Returns A2A service at {RETURNS_SERVICE_URL}")
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen(
        [sys.executable, "-m", "returns_service.server"],
        cwd=str(_backend_dir()),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
    )

    deadline = time.time() + 30.0
    while time.time() < deadline:
        try:
            httpx.get(RETURNS_CARD_URL, timeout=1.0).raise_for_status()
            print("[harness] Returns A2A service is ready.")
            return proc
        except Exception:
            if proc.poll() is not None:
                raise RuntimeError("returns_service.server exited before becoming ready")
            time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("returns_service.server failed to start within 30s")


def stop_returns_service(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    print("[harness] Stopping Returns A2A service ...")
    try:
        if sys.platform == "win32":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


# --------------------------------------------------------------------- #
# Runner                                                                #
# --------------------------------------------------------------------- #

async def run_scenario(runner: Runner, scenario: Scenario) -> None:
    print(f"\n{BAR}\nSCENARIO: {scenario.title}\n{BAR}")
    print(f"Intent: {scenario.intent}")
    print(SUB)

    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=scenario.session_id
    )

    for turn in scenario.turns:
        print(f"\nuser> {turn}")
        message = types.Content(role="user", parts=[types.Part(text=turn)])
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=scenario.session_id,
            new_message=message,
        ):
            _render_event(event)


async def main() -> None:
    proc = start_returns_service()
    try:
        runner = Runner(
            app_name=APP_NAME,
            agent=root_agent,
            session_service=InMemorySessionService(),
        )
        for scenario in SCENARIOS:
            await run_scenario(runner, scenario)
        print(f"\n{BAR}\nAll scenarios finished.\n{BAR}")
    finally:
        stop_returns_service(proc)


if __name__ == "__main__":
    asyncio.run(main())
