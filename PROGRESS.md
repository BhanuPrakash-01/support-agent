# PROGRESS.md

## Current State
- M0 complete; M1 complete (per-customer rolling summaries).
- refactor-001 complete: code now lives in the support_agent/ package
  (installable via `pip install -e .`), tests in tests/, DB in data/.
- summary-quality-001 complete: summarizer prompt tightened to <= 3 sentences,
  no 'Unknown'/'[Not specified]' placeholders, no name/plan, ticket-grounded facts only.
- close-ui-001 complete: Close Ticket section added to app.py. Picker shows only
  open tickets for the selected customer; resolution text required before Close button
  fires close_ticket(); page reruns to reflect updated summary. DB query moved into
  memory.get_open_tickets() to keep sqlite3 out of app.py (boundary check passes).
- Last verified: close-ui-001 — ./verify.sh exit 0 (14 tests, all layers green).
- Active feature: none.

## Next Action
Continue M2. Activate the next feature:
`python3 scripts/wip.py activate retrieval-001`
Goal: add support_agent/retrieval.py — a Chroma vector store that indexes a
customer's past closed tickets and exposes search_history(customer_id, query),
isolated by customer_id metadata filter.