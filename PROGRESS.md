# PROGRESS.md

## Current State
- M0 complete: walking-skeleton agent deployed, traced, tested.
- Harness installed (CLAUDE.md, docs/, feature_list.json [M1], verify.sh, scripts/).
- Last verified: M0 baseline — `./verify.sh` exit 0.
- Active feature: none.

## Next Action
Begin M1. Activate the first feature:
`python scripts/wip.py activate summary-001`
then implement the `summary` column in db_setup.py and make its verification pass.