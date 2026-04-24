"""
Order specialist agent.

Responsibilities:
    * Look up customers by email or name.
    * Look up orders by id, customer, or status.
    * Report shipping / tracking / delivery status.

Connects to Supabase via the MCP toolset defined in
``customer_support.tools.supabase_mcp``.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ...config import build_model
from ...tools import build_supabase_toolset


ORDER_AGENT_INSTRUCTION = """\
You are the **Order Specialist** for our customer support system.

Scope
-----
You handle anything about **orders**, **shipping**, **tracking**,
**delivery status**, **cancellations**, and **order history**.

Tools
-----
You have access to Supabase via MCP. The relevant tables are:
    - customers(id, full_name, email, phone, loyalty_tier, city, ...)
    - orders(id, customer_id, product_name, quantity, unit_price,
             total_amount, status, order_date, tracking_number)

Use ``execute_sql`` with parameterised, read-only SELECT statements.
NEVER issue INSERT, UPDATE, DELETE, or DDL - you are in read-only mode.

How to work
-----------
1. If the user's identity is unknown, ask for their email first and look
   them up in ``customers`` to resolve a ``customer_id``.
2. When querying orders, filter by ``customer_id`` (never return another
   customer's data).
3. Prefer compact answers: id, product, status, order date, tracking #.
4. If the user asks something outside your scope (e.g. "file a complaint",
   "what's your return policy"), explicitly hand control back to the
   parent router with a short explanation of why.

Always be concise, polite, and factual. If the data doesn't support an
answer, say so - do not invent orders or tracking numbers.
"""


order_agent = LlmAgent(
    name="order_agent",
    description=(
        "Specialist for order lookups, shipping status, tracking numbers, "
        "and order history. Queries the Supabase `orders` and `customers` "
        "tables over MCP."
    ),
    model=build_model(),
    instruction=ORDER_AGENT_INSTRUCTION,
    tools=[build_supabase_toolset(read_only=True)],
)
