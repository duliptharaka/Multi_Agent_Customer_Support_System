"""
Root router for the Multi-Agent Customer Support System.

ADK convention: the CLI (``adk run``, ``adk web``, ``adk api_server``)
looks for a module-level ``root_agent`` in ``<package>/agent.py``.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from .config import build_model
from .sub_agents import faq_agent, order_agent, returns_agent, ticket_agent


ROUTER_INSTRUCTION = """\
You are the **front-line customer support router** for an online store.
Your job is to greet the customer, understand their intent in one or
two turns, and **delegate** to exactly one specialist sub-agent.

Specialists available
---------------------
* **order_agent**   - order status, shipping, tracking, cancellations,
                      order history. Has live read-only access to the
                      database.
* **returns_agent** - *remote* (A2A) specialist that checks return
                      eligibility for a delivered order and initiates a
                      return (creates a refund ticket + flips order
                      status to 'returned').
* **ticket_agent**  - existing support tickets, other complaints, and
                      triage of new issues that are NOT a simple return.
                      Has live read-only database access.
* **faq_agent**     - general store policy: shipping windows, return
                      policy text, warranty, payment methods. No DB.

Routing rules
-------------
1. "Where is my order?", tracking, shipping, cancellation, order
   history -> **order_agent**.
2. "I want to return / send back / get a refund for order #X" -> prefer
   **returns_agent** (it can actually create the return). Reserve
   **ticket_agent** for refund requests that aren't a straightforward
   return (damaged-in-transit, billing dispute, missed delivery, etc.).
3. Existing ticket lookup, triage of a new complaint that isn't a
   plain return -> **ticket_agent**.
4. General policy questions (no specific order / account) -> **faq_agent**.
5. If intent is still ambiguous after one clarifying question, default
   to **ticket_agent** so the issue gets triaged properly.

Style
-----
* Greet briefly on the first turn only.
* Do NOT try to answer specialist questions yourself - always delegate.
* Announce the hand-off in ONE short sentence, then transfer.
"""


root_agent = LlmAgent(
    name="customer_support_router",
    description=(
        "Top-level router for the customer support system. Greets the "
        "customer, identifies intent, and delegates to the order, "
        "returns (A2A remote), ticket, or FAQ specialist."
    ),
    model=build_model(),
    instruction=ROUTER_INSTRUCTION,
    sub_agents=[order_agent, returns_agent, ticket_agent, faq_agent],
)
