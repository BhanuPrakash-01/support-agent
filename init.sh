#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "==> Working directory: $PWD"

if [ ! -d ".venv" ]; then
  echo "==> Creating virtualenv"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Installing dependencies"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "==> Building database from seed"
python db_setup.py >/dev/null

echo "==> Running verification gate"
if ! ./verify.sh; then
  echo "FAIL: can-verify (./verify.sh did not exit 0)"; exit 11
fi

echo "==> Verifying bootstrap contract"
if [ ! -f PROGRESS.md ] || ! grep -q "## Next Action" PROGRESS.md; then
  echo "FAIL: can-see-progress (PROGRESS.md missing or no Next Action)"; exit 12
fi
if [ ! -f feature_list.json ]; then
  echo "FAIL: can-pick-next-steps (feature_list.json missing)"; exit 13
fi
python scripts/wip.py status >/dev/null || { echo "FAIL: feature_list invalid"; exit 14; }

echo "OK: bootstrap contract holds"
echo "    can-verify          PASS"
echo "    can-see-progress    PASS"
echo "    can-pick-next-steps PASS"
echo
echo "State:"
python scripts/wip.py status | sed 's/^/    /'
echo
echo "Next action (from PROGRESS.md):"
awk '/^## Next Action/{flag=1; next} flag && NF {print "    " $0}' PROGRESS.md | head -3