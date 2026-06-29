# PROGRESS.md

## Current State
- M0 complete; M1 complete (per-customer rolling summaries).
- refactor-001 complete: code now lives in the support_agent/ package
  (installable via `pip install -e .`), tests in tests/, DB in data/.
- Last verified: refactor-001 — `./verify.sh` exit 0 on the new layout.
- Active feature: none.

## Next Action
Continue M2. Activate the next feature:
`python scripts/wip.py activate summary-quality-001`
Goal: tighten the summarizer prompt so summaries are <= 3 sentences, omit
name/plan (those come from columns), and state only ticket-grounded facts.