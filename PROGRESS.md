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
- retrieval-001 complete: support_agent/retrieval.py created with make_collection,
  index_ticket, search_history (ISOLATION: every query filters where={'customer_id'}),
  and backfill_index (reads DB via memory.get_closed_tickets to keep sqlite3 out of
  retrieval.py). agent.py rewritten with lazy client + tool loop (model_call/collection/
  embed/max_steps injectable). memory.py extended: get_closed_tickets(), close_ticket
  gains embed/collection params to index on close. All 21 tests pass, all layers green.
- Last verified: retrieval-001 — .venv/bin/python3 -m pytest 2 passed; ./verify.sh
  21 passed, all layers green.
- Active feature: none.

- tool-loop-001 complete: test_loop_executes_tool_call and test_loop_terminates confirmed
  passing. Implementation was delivered as part of retrieval-001 (agent.py tool loop).
- Last verified: tool-loop-001 — .venv/bin/python3 -m pytest 2 passed.
- Active feature: none.

## Next Action
Continue M2. Activate the next feature:
`python3 scripts/wip.py activate index-sync-001`
Goal: confirm test_closed_ticket_is_indexed and test_backfill_indexes_all pass
(already implemented); create scripts/backfill_embeddings.py.