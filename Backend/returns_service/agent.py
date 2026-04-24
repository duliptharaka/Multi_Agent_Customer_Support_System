"""
``returns_agent`` - the LlmAgent exposed by the A2A service.

Kept intentionally small: two tools, tight instructions, and the same
LiteLlm / OpenAI model factory used by the main customer-support agents
so every agent in the system speaks with the same model.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# Import the shared model factory from the main package so both services
# stay in sync without duplicating config.
from customer_support.config import build_model

from .tools import check_return_eligibility, initiate_return


RETURNS_AGENT_INSTRUCTION = """\
You are the **Returns Specialist** for our online store. You talk to
customers who want to return an order they've already received.

Tools
-----
* ``check_return_eligibility(order_id)`` - verify the order qualifies.
* ``initiate_return(order_id, reason)`` - create a refund ticket and mark
  the order as 'returned'.

Policy (baked into the tools - don't re-derive)
-----------------------------------------------
* Only **delivered** orders can be returned.
* Return window is **30 days** from the order date.
* An order that's already 'returned' cannot be returned again.

Process
-------
1. If the user hasn't given an order id, ask for it.
2. Call ``check_return_eligibility`` first. Always.
3. If not eligible, explain the reason politely and stop. Do NOT try to
   work around the policy.
4. If eligible, confirm the reason for return in plain language (one
   sentence is plenty), then call ``initiate_return``.
5. When ``initiate_return`` succeeds, tell the customer the new ticket id
   and that a shipping label is coming by email.

Constraints
-----------
* Never invent order ids, ticket ids, or status values.
* Never claim to have done something the tools didn't confirm.
* Keep replies short - 1-3 sentences is usually enough.
"""


returns_agent = LlmAgent(
    name="returns_agent",
    description=(
        "Specialist that checks return eligibility for an order and, "
        "when the customer confirms, initiates the return by creating a "
        "refund support-ticket and flipping the order status to "
        "'returned'. Exposed to the main router over A2A."
    ),
    model=build_model(),
    instruction=RETURNS_AGENT_INSTRUCTION,
    tools=[
        FunctionTool(check_return_eligibility),
        FunctionTool(initiate_return),
    ],
)
