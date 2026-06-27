#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
set -a; [ -f .env ] && . ./.env; set +a

step() { printf '\n==> %s\n' "$1"; }

# Run inside the project venv if it exists; the gate must use project deps.
if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

step "Layer 0: fresh database"
# Rebuild support.db from seed so tests run against a known state, never stale data.
python db_setup.py >/dev/null

step "Layer 1a: lint"
ruff check .

step "Layer 1b: architecture boundary — memory seam"
# memory.py owns all DB access. agent.py must never import sqlite3 directly.
if grep -nE '^\s*import\s+sqlite3|^\s*from\s+sqlite3' agent.py; then
  echo "BOUNDARY VIOLATION: agent.py accesses sqlite3 directly. DB access belongs in memory.py." >&2
  exit 1
fi

step "Layer 1c: isolation invariant"
# Every customer-table read must be scoped by customer_id. Flag any SELECT
# from customers/tickets that has no WHERE customer_id filter for review.
python scripts/check_isolation.py

step "Layer 2: unit + eval tests (offline, deterministic)"
# Tests use the stub summarizer — no network, no live model in the gate.
python -m pytest test_memory.py -q

step "Layer 3: smoke test — the agent still answers a ticket"
# The one layer that touches the real model. Skipped automatically when no
# GROQ_API_KEY is present (e.g. CI), so a missing key doesn't fail the gate.
if [ -n "${GROQ_API_KEY:-}" ]; then
  python scripts/smoke_test.py
else
  echo "SKIP: no GROQ_API_KEY set — smoke test skipped."
fi

step "Feature list integrity"
# feature_list.json must be valid JSON and obey WIP=1 (at most one in_progress).
python scripts/check_features.py

echo
echo "verify: ALL LAYERS GREEN"