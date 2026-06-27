# CLAUDE.md — support-agent

Memory-centric customer support agent. Work one feature at a time;
a feature is done only when verification passes.

## Hard constraints (read every session)
1. **WIP = 1.** Check `feature_list.json` before any work. If a feature is
   `in_progress`, finish it (or move it to `blocked` with a documented reason)
   before activating another.
2. **Isolation.** Every customer fetch uses `WHERE customer_id = ?`. Never
   broaden it — cross-customer leakage is a correctness bug, not a style choice.
   See `docs/ARCHITECTURE.md`.
3. **Verify before done.** A feature is not complete until `./verify.sh` exits 0.

## Topic docs
| Topic                       | File                   |
|-----------------------------|------------------------|
| Architecture & memory model | `docs/ARCHITECTURE.md` |
| Milestone roadmap           | `docs/ARCHITECTURE.md` |
| Style & conventions         | `docs/CONVENTIONS.md`  |
| Session log                 | `PROGRESS.md`          |
| Latest handoff              | `session-handoff.md`   |

## Where the code is
- `db_setup.py` — SQLite schema + seed data
- `memory.py` — `get_customer_context()`: the memory layer
- `agent.py` — `handle_ticket()`: the agent loop + retry-on-429
- `app.py` — Streamlit UI
- `test_memory.py` — eval checks (run by `verify.sh`)

## Workflow
1. `./init.sh` — must exit 0 before any work.
2. Read `PROGRESS.md` and `session-handoff.md`; pick the next item from `feature_list.json`.
3. Set that feature's status to `in_progress` in `feature_list.json`.
4. Implement — that feature only, no unrelated refactors.
5. `./verify.sh` — must be green before claiming done.
6. Set the feature's status to `done`.
7. Append to `PROGRESS.md`, write `session-handoff.md`, commit.

## Hard constraints (repeated)
1. One feature at a time (WIP = 1).
2. Every customer fetch uses `WHERE customer_id = ?`.
3. Not done until `./verify.sh` exits 0.