# PROGRESS.md

## Current State
- M0 complete; M1 complete (per-customer rolling summaries).
- refactor-001 complete: code now lives in the support_agent/ package
  (installable via `pip install -e .`), tests in tests/, DB in data/.
- summary-quality-001 complete: summarizer prompt tightened to <= 3 sentences,
  no 'Unknown'/'[Not specified]' placeholders, no name/plan, ticket-grounded facts only.
  Tests: test_summary_bounded, test_summary_no_unknown_placeholders — both passing.
- Last verified: summary-quality-001 — pytest 2 passed; ./verify.sh 14 passed.
- Active feature: none.

## Next Action
Continue M2. Activate the next feature:
`python3 scripts/wip.py activate close-ui-001`
Goal: add a Close Ticket button to the Streamlit UI so a user can pick an open
ticket, type a resolution, click Close, and the ticket is marked Closed with the
customer's summary updated — no terminal needed.