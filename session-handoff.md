# session-handoff.md

_Last session: harness installation. For the next session to pick up._

## What happened
- Built the full harness around the M0 agent: CLAUDE.md, docs/ARCHITECTURE.md,
  docs/CONVENTIONS.md, feature_list.json (M1), verify.sh, scripts/ (wip.py,
  check_boundaries.py, smoke_test.py, clean_exit.py), PROGRESS.md, DECISIONS.md.
- No application code changed; M0 behavior is unchanged.

## State
- Active feature: none. The WIP=1 slot is free.
- verify.sh: green on the M0 baseline.

## Next step
1. `./init.sh` — confirm the bootstrap contract holds (exit 0).
2. `python scripts/wip.py activate summary-001`.
3. Implement summary-001, then `python scripts/wip.py pass summary-001`
   to run its verification and record evidence.

## Watch-outs
- app.py's customer-dropdown query needs the `# allow: all-customers` waiver the
  first time check_boundaries.py runs against it.
- Export GROQ_API_KEY (or rely on verify.sh sourcing .env) for the smoke test.