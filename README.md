# Multi-Agent Customer Support System

A small end-to-end demo: a **router agent** built with
[Google ADK](https://google.github.io/adk-docs/) delegates to four
specialist sub-agents — Orders, Returns (remote A2A), Tickets, and FAQ.
Two of the local specialists query Supabase live through the official
[Supabase MCP server](https://supabase.com/docs/guides/getting-started/mcp),
and the Returns specialist runs as its **own HTTP service** reached over
the [A2A protocol](https://google.github.io/adk-docs/a2a/).
A Streamlit Frontend (Step 4) will talk to the Backend over ADK's HTTP
API and provide a chat UI.

## Repo layout

```
.
├── .env                       # all secrets (git-ignored)
├── requirements.txt           # shared deps for Backend + Frontend
├── Backend/
│   ├── customer_support/      # main ADK agent package (root_agent + specialists)
│   │   ├── agent.py           # root_agent (router)
│   │   ├── config.py          # shared LiteLlm model factory
│   │   ├── sub_agents/
│   │   │   ├── order_agent/   # orders / shipping / tracking   (Supabase MCP)
│   │   │   ├── ticket_agent/  # tickets / complaints / triage  (Supabase MCP)
│   │   │   ├── faq_agent/     # policies, no DB access
│   │   │   └── returns_agent.py  # RemoteA2aAgent -> returns_service
│   │   └── tools/
│   │       └── supabase_mcp.py
│   ├── returns_service/       # separate A2A service (Step 3)
│   │   ├── agent.py           # returns_agent (LlmAgent + 2 tools)
│   │   ├── tools.py           # check_return_eligibility, initiate_return
│   │   ├── db.py              # Supabase Management API SQL helper (read+write)
│   │   └── server.py          # to_a2a(agent) + uvicorn entrypoint (port 8001)
│   ├── database/
│   │   ├── schema.sql         # tables + 45 seed rows
│   │   └── README.md          # how to run the SQL in Supabase
│   └── tests/
│       └── scenarios.py       # end-to-end: billing (MCP) + returns (A2A) + escalation
└── Frontend/                  # Streamlit chat UI (Step 5, not built yet)
```

## Architecture

```
                     ┌───────────────────────────────┐
  user ───────────▶  │ customer_support_router       │  root_agent (LlmAgent)
                     │  greets · classifies · routes │
                     └──────────────┬────────────────┘
                                    │ sub_agent transfer
        ┌──────────────────┬────────┴────────┬────────────────────┐
        ▼                  ▼                 ▼                    ▼
 ┌──────────────┐  ┌──────────────┐   ┌──────────────┐    ┌──────────────┐
 │ order_agent  │  │ returns_agent│   │ ticket_agent │    │  faq_agent   │
 │  (LlmAgent)  │  │(RemoteA2aAg.)│   │  (LlmAgent)  │    │  (LlmAgent)  │
 └──────┬───────┘  └──────┬───────┘   └──────┬───────┘    └──────────────┘
        │  MCPToolset     │ A2A JSON-RPC     │  MCPToolset   (no tools)
        ▼                 ▼ (port 8001)      ▼
 ┌────────────────┐  ┌─────────────────┐  ┌────────────────┐
 │ Supabase MCP   │  │ returns_service │  │ Supabase MCP   │
 │ (read-only)    │  │ (LlmAgent +     │  │ (read-only)    │
 └────────┬───────┘  │  2 FunctionTools│  └────────┬───────┘
          │          └─────┬───────────┘           │
          │                │ httpx                 │
          │                ▼                       │
          │        ┌──────────────────┐            │
          │        │ Supabase Mgmt API│            │
          │        │ (read + write)   │            │
          │        └─────────┬────────┘            │
          ▼                  ▼                     ▼
        ┌────────────────────────────────────────────┐
        │                  Supabase                  │
        │   customers · orders · support_tickets     │
        └────────────────────────────────────────────┘
```

## Prerequisites

* **Python 3.13** (3.14 is fresh; not every ADK/LiteLLM dep has wheels for it yet)
* **Node.js 18+** — `npx` launches the Supabase MCP server
* A Supabase project with [`Backend/database/schema.sql`](Backend/database/README.md) already applied (Step 1)

## Setup

A **single shared venv** lives at `C:\Users\dmadura\.venvs\cs-agents`
(placed outside the project because the deeply-nested project path
collides with Windows' 260-char path limit when `litellm`'s proxy UI
assets unpack). Both Backend and Frontend use it, driven by the one
`requirements.txt` at the repo root.

From the repo root:

```powershell
# 1. One-time: create the venv and install everything
py -3.13 -m venv C:\Users\dmadura\.venvs\cs-agents
C:\Users\dmadura\.venvs\cs-agents\Scripts\python.exe -m pip install --upgrade pip
C:\Users\dmadura\.venvs\cs-agents\Scripts\python.exe -m pip install -r requirements.txt

# 2. Activate for an interactive session
C:\Users\dmadura\.venvs\cs-agents\Scripts\Activate.ps1
```

### Environment variables

All secrets live in a **single** `.env` at the **repo root** (git-ignored).
The ADK package loads it automatically from
`Backend/customer_support/__init__.py`, so running `adk ...` from
`Backend/` (or Streamlit from `Frontend/`) picks them up without any
activation gymnastics.

| Var                     | Where to get it                                             |
| ----------------------- | ----------------------------------------------------------- |
| `OPENAI_API_KEY`        | OpenAI dashboard                                            |
| `OPENAI_MODEL`          | e.g. `gpt-4o-mini`                                          |
| `SUPABASE_ACCESS_TOKEN` | Supabase dashboard -> Account -> **Access Tokens**          |
| `SUPABASE_PROJECT_REF`  | Either the short id or the full `https://<ref>.supabase.co` |

> `SUPABASE_PROJECT_REF` tolerates either form — the loader extracts the
> short id from a URL if needed (see `Backend/customer_support/tools/supabase_mcp.py`).

> The Supabase MCP server needs a **personal access token**, not the
> anon/service-role key. The server is started in `--read-only` mode by
> default, so agents cannot modify data.

## Database (Step 1)

See [`Backend/database/README.md`](Backend/database/README.md) for the
full schema walk-through. TL;DR: paste `schema.sql` into Supabase →
**SQL Editor** → **Run**. You should get 15 rows each in
`customers`, `orders`, and `support_tickets`.

## Backend (Step 2) — running the local agents

The Returns A2A service in Step 3 must be started **before** `adk web`,
otherwise the router's `RemoteA2aAgent` can't fetch the remote agent
card at startup.

Open **two** terminals from the repo root (venv active in both, or use
the absolute path `C:\Users\dmadura\.venvs\cs-agents\Scripts\...`).

### Terminal A — Returns A2A service (keep running)

```powershell
cd Backend
python -m returns_service.server      # listens on http://127.0.0.1:8001
```

### Terminal B — the rest of the system

```powershell
cd Backend

# Interactive web UI (best for demos)
adk web

# ...or the CLI
adk run customer_support

# ...or the HTTP API server (used by the Frontend in Step 4)
adk api_server
```

`adk web` opens at http://localhost:8000 — pick **customer_support** in
the agent dropdown.

### Try it

* *"Where's my order? My email is alice.johnson@example.com"*
  → router → `order_agent` → queries `orders` via Supabase MCP.
* *"I want to return order #4, it's a dud."*
  → router → `returns_agent` (remote) → calls `check_return_eligibility`
  on the A2A service; if eligible, prompts for confirmation, then calls
  `initiate_return`, which creates a refund ticket and flips the order
  to `returned`.
* *"I want to open a complaint about my espresso machine."*
  → router → `ticket_agent` → returns a triage summary.
* *"How long do international shipments take?"*
  → router → `faq_agent` → answers from the baked-in policy.

## Step 3 — the Returns Agent via A2A

Why a separate service? It demonstrates the exact pattern ADK's A2A
support is designed for: a specialist that lives in its **own process**
(could be on another machine / in another language / owned by another
team) joins the multi-agent conversation through a standard contract.

### Moving parts

| File                                                            | Role                                                                                       |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `Backend/returns_service/tools.py`                              | Pure Python: `check_return_eligibility(order_id)` and `initiate_return(order_id, reason)`. |
| `Backend/returns_service/db.py`                                 | Thin `httpx` client for Supabase's Management API SQL endpoint (read + write).             |
| `Backend/returns_service/agent.py`                              | `LlmAgent` that wraps the two tools with `FunctionTool`.                                   |
| `Backend/returns_service/server.py`                             | `to_a2a(returns_agent, host, port)` → Starlette app served by uvicorn on port 8001.        |
| `Backend/customer_support/sub_agents/returns_agent.py`          | `RemoteA2aAgent` pointing at `http://127.0.0.1:8001/.well-known/agent-card.json`.          |

### Return-policy rules (enforced in the tool, not just prompted)

* Only orders with `status = 'delivered'` can be returned.
* Return window = **30 days** from `order_date`.
* Orders already `status = 'returned'` can't be returned again.

### Override the Returns-service location

Set either of these before starting `adk`:

```powershell
$env:RETURNS_SERVICE_HOST = "0.0.0.0"     # read by returns_service/server.py
$env:RETURNS_SERVICE_PORT = "9000"
$env:RETURNS_AGENT_URL    = "http://some-host:9000"   # read by the RemoteA2aAgent
```

### MCP connection details (Step 2 agents)

`Backend/customer_support/tools/supabase_mcp.py` wraps the MCP server
as an ADK `MCPToolset` in `--read-only` mode, filtered to
`list_tables`, `list_extensions`, `execute_sql`. The Returns service
intentionally bypasses MCP and hits the Supabase Management API
directly because it needs to **write** (INSERT a ticket, UPDATE the
order status). That keeps the MCP surface safely read-only for the
rest of the system.

## Step 4 — end-to-end scenarios

`Backend/tests/scenarios.py` drives the full system through three
scripted conversations and prints every router hand-off, tool call,
and tool response. It **auto-starts** the Returns A2A service as a
subprocess if one isn't already running on port 8001 — so a single
command exercises everything.

```powershell
cd Backend
C:\Users\dmadura\.venvs\cs-agents\Scripts\python.exe -m tests.scenarios
```

| # | Scenario    | What it proves                                                                                       |
| - | ----------- | ---------------------------------------------------------------------------------------------------- |
| 1 | Billing     | Router → `ticket_agent` → MCP `execute_sql` (two SELECTs) → ticket #8 surfaced from Supabase.        |
| 2 | Returns     | Router → `returns_agent` **(A2A)** → remote `check_return_eligibility` → remote `initiate_return` → real INSERT into `support_tickets` + UPDATE on `orders.status`. |
| 3 | Escalation  | Router → `returns_agent` (rejects: out-of-window) → user asks to escalate → Router → `ticket_agent` → MCP lookup of related technical ticket.                       |

### Notes

* **Scenario 2 is a real write.** On the first run it creates a new
  `support_ticket` (id `16` in the sample run) and flips order #7 to
  `returned`. On the next run the same order is correctly refused
  ("already returned") — which is itself proof the idempotency guard
  in `check_return_eligibility` works. Re-apply `Backend/database/schema.sql`
  to reset.
* **Remote tool calls are invisible to the local stream.** By A2A
  protocol design, the local router only receives the remote agent's
  *messages*, not its internal function-call events. Scenario 2's
  proof of tool execution is the new ticket in Supabase, not a log
  line.
* The harness pre-suppresses LiteLLM's noisy "Provider List" banner
  and ADK's experimental-feature warnings so the scenario output stays
  readable.

## Frontend (Step 5) — not built yet

Planned as a **Streamlit** chat UI that talks to `adk api_server`
(session create → `run_sse` streaming) so the conversation state and
sub-agent transfers are visible. Once implemented it will live under
`Frontend/` and be launched with:

```powershell
cd Frontend
streamlit run app.py
```

(Placeholder — this section will be fleshed out in Step 5.)
