# ARCHITECTURE.md — support-agent

Memory-centric support agent: answers each ticket in the context of the
customer's history, rather than treating tickets as isolated events.

## System shape (current — M0)
- `db_setup.py` — SQLite schema + seed data (`support.db`)
- `memory.py` — `get_customer_context(customer_id)`: fetches a customer's
  profile + past tickets, formats them into a text block. **All DB access for
  memory lives here.** `agent.py` never queries the DB directly.
- `agent.py` — `handle_ticket(customer_id, message)`: assembles context, calls
  the model (Groq, OpenAI-compatible) with retry-on-429, returns the reply.
  Structured as an agent loop with no tools registered yet.
- `app.py` — Streamlit UI (customer dropdown → ticket box → reply).
- `test_memory.py` — eval checks (recall, isolation, unknown-customer).
- Tracing: Langfuse wraps `handle_ticket`. Deploy: Streamlit Community Cloud.

### Ticket flow
1. UI passes `customer_id` + message to `handle_ticket`.
2. `handle_ticket` calls `get_customer_context` → context string.
3. Prompt = system + context + new message → model.
4. Reply returned to UI; whole interaction logged as one Langfuse trace.

## Data model
Two tables, linked by `customer_id` (foreign key).
- `customers`: `customer_id`, `name`, `plan`, `created_at`
- `tickets`: `ticket_id`, `customer_id`, `subject`, `body`, `status`,
  `resolution` (nullable — open tickets have none), `created_at`

**Isolation invariant:** a customer's data is always read with
`WHERE customer_id = ?`. This is both how memory is fetched and how one
customer's history is prevented from leaking into another's context.

## Memory model (target — built across milestones)
Three memory types, in two scopes. M0 implements only raw fetch-and-format;
each layer below is added by a later milestone.

- **Raw** (per customer) — verbatim tickets in SQLite. Source of truth, never
  discarded, rarely sent to the model whole.
- **Semantic** (per customer) — a rolling profile summary, LLM-updated when a
  ticket closes. Cheap, always injected. *(M1)*
- **Episodic retrieval** (per customer) — specific past tickets fetched by
  meaning (vector search), exposed as a tool the model chooses to call. *(M2,
  scored in M3)*
- **Structured facts** (per customer) — discrete timestamped facts so newer
  ones supersede stale ones. *(M4)*
- **Resolution playbook** (GLOBAL, anonymized, no PII) — cross-customer
  "problem class → fix that worked." Not partitioned by customer. *(M5)*
- **Reflection** — periodic LLM pass forming higher-order insights from a
  customer's history. *(M6)*

Two scopes: per-customer (isolated via the invariant above) and global
(shared, but anonymized — the playbook must contain no customer-identifying data).

## Milestone roadmap
The single source of truth for scope. `feature_list.json` breaks the *active*
milestone into features; this table is the high-level plan.

| Milestone | Adds                                          | Key new artifact                        |
|-----------|-----------------------------------------------|-----------------------------------------|
| M0 ✅      | Walking skeleton, deployed + traced + tested  | the files above                         |
| M1        | Semantic summary, LLM-updated on ticket close | summary store + update function         |
| M2        | Episodic retrieval as a model-callable tool   | Chroma + sentence-transformers + tool   |
| M3        | Scored retrieval (recency + importance + relevance) | scoring fn; importance at write-time |
| M4        | Structured facts + contradiction handling     | `facts` table (`valid` flag, timestamps)|
| M5        | Global resolution playbook (anonymized)       | second Chroma collection, no PII        |
| M6        | Reflection (insights across history)          | reflection fn, triggered on Nth ticket  |

## Architectural invariants
- **Memory seam:** all memory logic stays in `memory.py`. Smarter memory =
  changes there, not scattered across `agent.py`.
- **Tool-ready loop:** `handle_ticket` is shaped so M2 adds retrieval as a
  *registered tool*, not a rewrite of the loop.
- **Free-tier discipline:** keep retry-on-429; default to a small Groq model;
  run embeddings locally (sentence-transformers) so retrieval costs nothing.
- **Isolation:** see the data-model invariant. Never widen a customer query.