# PROGRESS.md

## Current State
- M0 complete: walking-skeleton agent deployed, traced, tested.
- **M1 complete**: all 6 features passing (summary-001 through ui-006). VCR=1.00 (6/6).
- Last verified: `./verify.sh` exit 0 (12 tests green).
- Active feature: none.

## Session log

### 2026-06-27 — summary-001
- Added nullable `summary TEXT` column to `customers` table in `db_setup.py`.
- Updated seed INSERT to use explicit column names so re-runs are safe.
- Added `test_customers_has_summary_column` to `test_memory.py`.
- `python3 scripts/wip.py pass summary-001` → passing, evidence recorded.
- `./verify.sh` → ALL LAYERS GREEN (4 tests).

### 2026-06-27 — summary-002
- Added `_default_summarizer` (Groq + retry-on-429) and `update_customer_summary(customer_id, ticket, summarizer=None)` to `memory.py`.
- Added `test_summary_update_first_time` and `test_summary_update_persists` to `test_memory.py` (deterministic stubs, no network).
- Fixed lambda → def to satisfy linter (E731).
- `python3 scripts/wip.py pass summary-002` → passing, evidence recorded.
- `./verify.sh` → ALL LAYERS GREEN (6 tests).

### 2026-06-27 — memory-003
- Added `close_ticket(ticket_id, resolution, summarizer=None)` to `memory.py`.
- Ticket-scoped queries carry `# allow: all-customers` waiver (scoped by ticket_id, not customer_id).
- Added `test_close_ticket_persists` and `test_close_ticket_isolation` to `test_memory.py`.
- `python3 scripts/wip.py pass memory-003` → passing, evidence recorded.
- `./verify.sh` → ALL LAYERS GREEN (8 tests).

### 2026-06-27 — memory-004
- Updated `get_customer_context` to select `summary` and prepend `Profile summary: <text>` above the ticket list when non-null; NULL renders cleanly (no "None" literal).
- Added `test_summary_injected` and `test_no_summary_renders` to `test_memory.py`; M0 recall + isolation tests re-run as regression gate.
- `python3 scripts/wip.py pass memory-004` → passing, evidence recorded.
- `./verify.sh` → ALL LAYERS GREEN (10 tests).

### 2026-06-27 — backfill-005
- Added `backfill_summaries(summarizer=None)` to `memory.py`: resets all summaries to NULL then folds CLOSED tickets per customer in chronological order. `UPDATE customers SET summary = NULL` carries `# allow: all-customers` waiver.
- Created `scripts/backfill_summaries.py` as a CLI runner (calls `backfill_summaries()` from memory.py).
- Added `test_backfill_excludes_open_tickets` (1003's open ticket → summary stays NULL) and `test_backfill_idempotent` (counter-based stub, two runs produce identical state).
- `python3 scripts/wip.py pass backfill-005` → passing, evidence recorded.
- `./verify.sh` → ALL LAYERS GREEN (12 tests).

### 2026-06-27 — ui-006
- Added `get_customer_summary(customer_id)` to `memory.py` (thin accessor, keeps DB behind the memory seam).
- Updated `app.py`: title → "Support agent (M1)", imports `get_customer_summary`, displays an expanded `st.expander("Customer summary (read-only)")` between the customer selector and the ticket input. Shows a caption when no summary is on file.
- `./verify.sh` → ALL LAYERS GREEN (12 tests). `python3 scripts/wip.py pass ui-006` → passing, evidence recorded. VCR=1.00 (6/6).

## Next Action
M1 is complete. Await M2 spec or next instructions.