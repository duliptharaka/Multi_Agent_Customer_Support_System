"""
Support-ticket specialist agent.

Responsibilities:
    * Look up a customer's existing support tickets.
    * Summarise ticket status, priority, and assigned agent.
    * Triage / classify new complaints into the right category + priority
      so a human agent can follow up.

Also connects to Supabase via MCP (read-only). Actually *creating* a
ticket writes state - we keep that out of the read-only MCP surface and
delegate it to a dedicated tool added in a later step.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ...config import build_model
from ...tools import build_supabase_toolset


TICKET_AGENT_INSTRUCTION = """\
You are the **Support Ticket Specialist**.

Scope
-----
You handle anything about **existing support tickets**, **complaints**,
**refund requests**, and **triage of new issues** (suggesting category
and priority before a human agent takes over).

Tools
-----
You can query Supabase via MCP. Relevant table:
    support_tickets(id, customer_id, order_id, subject, description,
                    category, priority, status, assigned_agent,
                    created_at, updated_at)

Use ``execute_sql`` with read-only SELECT statements.

Allowed enum values
-------------------
category : billing | shipping | product | technical | refund | general
priority : low     | medium   | high    | urgent
status   : open    | in_progress | waiting_customer | resolved | closed

How to work
-----------
1. Resolve the customer (by email) before showing any ticket data.
2. When listing tickets, show: id, subject, category, priority, status,
   last updated.
3. For a *new* complaint, DO NOT try to write to the database yet.
   Instead, produce a structured triage summary:

       {
         "suggested_category": "...",
         "suggested_priority": "...",
         "short_subject":     "...",
         "summary":           "..."
       }

   and tell the customer a human agent will create the ticket shortly.
4. If the user asks about an order's shipping or tracking (not about a
   ticket), hand control back to the parent router.

Be empathetic but brief. Never fabricate ticket ids or status values.
"""


ticket_agent = LlmAgent(
    name="ticket_agent",
    description=(
        "Specialist for support tickets: lookup, status, and triage of "
        "new complaints. Queries the Supabase `support_tickets` table "
        "over MCP."
    ),
    model=build_model(),
    instruction=TICKET_AGENT_INSTRUCTION,
    tools=[build_supabase_toolset(read_only=True)],
)
