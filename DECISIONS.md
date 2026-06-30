# DECISIONS.md

Append-only. Each entry: id, date, decision, context, consequence.
Strike through when superseded — never delete.

## D-001 — SQLite + local files are the only persistence
- Date: 2026-06 (M0)
- Context: A production tool might use Postgres + a managed vector DB. This
  project optimizes for zero cost on an M1 Air, so it's SQLite (raw memory) and
  a local Chroma store (retrieval, from M2).
- Consequence: Everything runs offline and free; scaling limits are accepted.

## D-002 — All DB access lives in memory.py (the memory seam)
- Date: 2026-06 (M0)
- Context: Scattered queries make the isolation rule and later memory upgrades
  impossible to reason about.
- Consequence: agent.py never imports sqlite3. check_boundaries.py enforces it.

## D-003 — Isolation is a correctness invariant
- Date: 2026-06 (M0)
- Context: One customer's history must never surface in another's context.
- Consequence: Every customer read is scoped `WHERE customer_id = ?`. Broad reads
  need an explicit `# allow: all-customers` waiver. Enforced by check_boundaries.py.

## D-004 — Summaries fold in CLOSED tickets only
- Date: 2026-06 (M1)
- Context: Folding an open ticket into the summary would let it claim a
  resolution that never happened.
- Consequence: close_ticket is the only path that updates a summary; open tickets
  (e.g. 1003's refund) are excluded until closed.

## D-005 — The verification gate stays offline and deterministic
- Date: 2026-06 (M1)
- Context: LLM output is nondeterministic and the free tier is rate-limited; an
  LLM call inside the gate would make it flaky.
- Consequence: LLM functions take an injectable summarizer; tests use a stub. The
  live model is exercised only by the skippable smoke test. Tests assert
  structural properties, never exact wording.

## D-006 — Application code lives in an installable package (support_agent/)
- Date: 2026-06 (M2 / refactor-001)
- Context: A flat root mixed app code, harness scripts, and config; imports
  were fragile and M2 adds more modules.
- Consequence: All app code is under support_agent/, installed with
  `pip install -e .` so imports resolve identically from pytest, scripts, and
  Streamlit. DB_PATH is defined once in support_agent/__init__.py. db_setup
  builds the DB only when run explicitly (build_database), never on import.
  The app.py dropdown query moved into memory.list_customers(), restoring the
  memory seam (app.py no longer touches sqlite3).

## D-007 — Single Chroma collection with customer_id metadata filter (not per-customer collections)
- Date: 2026-06 (M2 / retrieval-001)
- Context: One collection per customer is simpler to reason about but requires
  creating a new collection for every new customer and makes cross-customer
  analytics impossible. A single collection with metadata is the Chroma-idiomatic
  pattern and keeps ops simple.
- Consequence: All tickets share the collection named "tickets". Every index call
  stores `{"ticket_id": ..., "customer_id": ...}` in metadata. Every search passes
  `where={"customer_id": cid}` — structurally enforced, not optional. check_boundaries.py
  cannot inspect Chroma, so test_search_isolation is the only guard; it is load-bearing.

## D-008 — Closing a ticket is always human-initiated, never automatic
- Date: 2026-06 (M2 / close-ui-001)
- Context: Closing a ticket is irreversible — it marks the ticket Closed, updates
  the customer's rolling summary, and (from retrieval-001) indexes the ticket into
  the vector store. An accidental or automatic close corrupts the summary and the index.
- Consequence: The Close Ticket path in the UI requires a human to select the ticket,
  type a resolution, and click the button. The agent never calls close_ticket. No
  automatic or timer-based close mechanism is permitted.

## D-009 — retrieval.py must not import sqlite3 (memory seam extends to the vector layer)
- Date: 2026-06 (M2 / retrieval-001)
- Context: D-002 established that all DB access lives in memory.py. retrieval.py needs
  closed-ticket data for backfill but adding sqlite3 there would breach the seam and
  scatter raw queries across modules.
- Consequence: retrieval.backfill_index() reads the DB by calling
  memory.get_closed_tickets() via a lazy import (avoiding a circular import at module
  load time). check_boundaries.py scans retrieval.py and would flag any sqlite3 import.

## D-010 — handle_ticket is fully injectable for deterministic offline testing
- Date: 2026-06 (M2 / tool-loop-001)
- Context: The tool loop calls the model (Groq) and the vector store — both are
  stateful and network-dependent. Extends D-005's stub-summarizer pattern to the agent.
- Consequence: handle_ticket gains model_call, collection, embed, and max_steps
  parameters. When None (default), the real Groq client and real collection are used.
  Tests inject stub functions; no network call or model download is required in the gate.
  The Groq client itself is lazily initialised so imports succeed without GROQ_API_KEY.

## D-011 — UI retrieval surfacing via a proxy wrapper, not a changed return type
- Date: 2026-06 (M2 / lock-m2-001)
- Context: The UI needs to show whether the model retrieved past tickets for a reply.
  Changing handle_ticket's return type from str to a tuple would break every existing
  call site and test.
- Consequence: app.py wraps the collection in _TracingCollection, which counts
  collection.query() calls without touching agent.py. After the reply, the UI shows
  "N search(es) used" or "answered directly". The agent API stays stable (returns str).

## D-012 — Summarizer prompt constraints: ≤3 sentences, no placeholders, ticket-grounded only
- Date: 2026-06 (M2 / summary-quality-001)
- Context: The original prompt produced verbose summaries with invented sentiment and
  placeholder text ('Unknown', '[Not specified]') when ticket data was sparse.
- Consequence: The prompt explicitly forbids name/plan (stored in columns), placeholder
  strings, invented sentiment, and limits output to 3 sentences. Missing facts are
  omitted rather than substituted. Tests assert structural properties (sentence count,
  absence of forbidden strings) using stub summarizers — never exact wording (per D-005).
  