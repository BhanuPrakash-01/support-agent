# session-handoff.md

_Last session: close-ui-001 (close-ticket button). For the next session._

## What happened
- Added `get_open_tickets(customer_id)` to `support_agent/memory.py` — returns
  `[(ticket_id, subject), ...]` for all Open tickets scoped to one customer.
- Updated `app.py`: Close Ticket section below the agent reply area.
  - Picker lists only open tickets for the selected customer.
  - Resolution text area is required before the Close button fires.
  - On click: `close_ticket()` marks ticket Closed and updates the customer summary,
    then `st.rerun()` refreshes the summary expander.
  - `sqlite3` stays out of `app.py` (boundary check confirmed OK).
- Bumped title to "Support agent (M2)".
- All 14 tests pass; ./verify.sh all layers green.

## State
- On main, committed, `./verify.sh` green. WIP slot is free.
- close-ui-001: `passing` with evidence.

## Next step
1. `python3 scripts/wip.py activate retrieval-001`
2. Create `support_agent/retrieval.py` with a Chroma collection (MiniLM embeddings,
   `customer_id` in metadata) and `search_history(customer_id, query)` that always
   filters `where={'customer_id': cid}`.
3. Create `tests/test_retrieval.py` with `test_search_returns_relevant` and
   `test_search_isolation` (index two customers, assert no cross-leak).
4. Add `chromadb` and `sentence-transformers` to `requirements.txt`.
5. Gate: `python3 -m pytest tests/test_retrieval.py::test_search_returns_relevant tests/test_retrieval.py::test_search_isolation -q`

## Watch-outs
- `close_ticket` scopes by ticket_id (safe), but `check_boundaries.py` only
  recognises `customer_id` — those two queries still carry `# allow: all-customers`.
- Chroma + sentence-transformers pull in torch, which is heavy on Streamlit Cloud.
  Solve the deploy concern at lock-m2-001, not now.
- First run of retrieval-001 will download MiniLM (~80 MB). Use a tmp dir in tests
  so the Chroma data doesn't land in data/chroma/ during test runs.
