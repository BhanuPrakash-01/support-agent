# Support Agent — memory-centric customer support (M0)

A customer support agent that answers tickets *in the context of a customer's history*,
rather than treating each ticket as an isolated event. This is the M0 "walking skeleton":
a complete, deployed pipeline with deliberately primitive memory, built as the foundation
for later milestones (semantic retrieval, scored memory, a global resolution playbook, and reflection).

## What it does
- Looks up the customer's profile and past tickets
- Feeds that history to an LLM alongside the new ticket
- Produces a reply that acknowledges prior issues and their resolutions ("the recall moment")

## Live demo
[your-app.streamlit.app](https://your-app.streamlit.app)

## Architecture (M0)
- **Database** — SQLite (`customers`, `tickets`), linked by `customer_id`
- **Memory** — `get_customer_context()` fetches and formats a customer's history into the prompt
- **Agent** — `handle_ticket()` assembles context, calls the model with retry-on-429, returns the reply
- **Model** — Llama 3.1 8B via Groq's free, OpenAI-compatible API
- **UI** — Streamlit
- **Tracing** — Langfuse (every interaction is inspectable)
- **Deployment** — Streamlit Community Cloud

## Memory isolation
Each customer's history is fetched with `WHERE customer_id = ?`, so one customer's
data can never surface in another's context. This is the foundation for the
per-customer vs. global memory scopes in later milestones.

## Running locally
1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. Create a `.env` with `GROQ_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
4. `python db_setup.py`
5. `streamlit run app.py`

## Roadmap
- **M1** — real episodic + semantic memory; LLM-updated customer summary on ticket close
- **M2** — semantic retrieval exposed as a tool the model chooses to call
- **M3** — scored retrieval (recency + importance + relevance)
- **M4** — structured facts with contradiction/temporal handling
- **M5** — global resolution playbook (anonymized, cross-customer)
- **M6** — reflection (higher-order insights across a customer's history)