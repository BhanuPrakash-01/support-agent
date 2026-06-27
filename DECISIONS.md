# DECISIONS.md

Append-only. Each entry: id, date, decision, context, consequence.
Strike through when superseded — never delete.

## D-001 — SQLite + local files are the only persistence
- Date: 2026-06 (M0)
- Context: A production tool might use Postgres + a managed vector DB. This
  project optimizes for zero cost on an M1 Air, so it's SQLite (raw memory) and
  a local Chroma store (retrieval, from M2).
- Consequence: Everything runs offline and free; scaling limits are accepted.

## D-002 — All DB access lives in memory.py (the memory seam)
- Date: 2026-06 (M0)
- Context: Scattered queries make the isolation rule and later memory upgrades
  impossible to reason about.
- Consequence: agent.py never imports sqlite3. check_boundaries.py enforces it.

## D-003 — Isolation is a correctness invariant
- Date: 2026-06 (M0)
- Context: One customer's history must never surface in another's context.
- Consequence: Every customer read is scoped `WHERE customer_id = ?`. Broad reads
  need an explicit `# allow: all-customers` waiver. Enforced by check_boundaries.py.

## D-004 — Summaries fold in CLOSED tickets only
- Date: 2026-06 (M1)
- Context: Folding an open ticket into the summary would let it claim a
  resolution that never happened.
- Consequence: close_ticket is the only path that updates a summary; open tickets
  (e.g. 1003's refund) are excluded until closed.

## D-005 — The verification gate stays offline and deterministic
- Date: 2026-06 (M1)
- Context: LLM output is nondeterministic and the free tier is rate-limited; an
  LLM call inside the gate would make it flaky.
- Consequence: LLM functions take an injectable summarizer; tests use a stub. The
  live model is exercised only by the skippable smoke test. Tests assert
  structural properties, never exact wording.