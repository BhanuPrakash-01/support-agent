# session-handoff.md

_Last session: ui-006 — M1 complete. For the next session to pick up._

## What happened
- Added `get_customer_summary(customer_id)` to `memory.py` (returns the stored summary or None, keeps sqlite3 behind the memory seam).
- Updated `app.py`: title bumped to M1, summary surfaced as a read-only `st.expander` between the customer selector and ticket input. Graceful fallback caption when summary is NULL.
- `./verify.sh` → ALL LAYERS GREEN (12 tests, VCR=1.00 after passing).

## State
- **M1 complete.** All 6 features passing: summary-001, summary-002, memory-003, memory-004, backfill-005, ui-006.
- verify.sh: green.
- Active feature: none. WIP slot is free.

## Next step
M1 is done. Await M2 spec.

## Manual checks still outstanding (per ui-006 notes)
- [ ] Visually confirm summary displays in the Streamlit UI for a customer with a non-null summary (run `backfill_summaries` first or close a ticket to generate one).
- [ ] Confirm one Langfuse trace shows the `Profile summary:` line inside the assembled context passed to the model.
These are not automated gate items but should be recorded in evidence notes if desired.
