#!/usr/bin/env python3
"""clean_exit.py — end-of-session lifecycle check.
Hand off only when every dimension is green. Heavier than verify.sh (it also
runs init.sh and checks git cleanliness) — run it at session end, not every loop.
"""
import subprocess, sys, pathlib

fails = 0
def check(name, fn):
    global fails
    try: fn(); print(f"  {name:<22} PASS")
    except Exception as e: print(f"  {name:<22} FAIL — {e}"); fails += 1

def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip() or f"exit {r.returncode}")

print("clean-exit dimensions:")

def progress_ok():
    md = pathlib.Path("PROGRESS.md").read_text()
    if "## Next Action" not in md: raise RuntimeError("no Next Action section")
    if md.rstrip().endswith("TODO"): raise RuntimeError("Next Action still says TODO")
check("progress", progress_ok)

check("feature list", lambda: sh("python scripts/wip.py status"))

def artifacts_ok():
    dirty = subprocess.run("git status --porcelain", shell=True,
                           capture_output=True, text=True).stdout.strip()
    if dirty: raise RuntimeError("uncommitted changes present")
    scratch = subprocess.run(
        "git ls-files --others --exclude-standard | grep -E '\\.(tmp|swp|bak)$|\\.DS_Store$' || true",
        shell=True, capture_output=True, text=True).stdout.strip()
    if scratch: raise RuntimeError("scratch files: " + scratch)
check("artifacts", artifacts_ok)

check("bootstrap (init.sh)", lambda: sh("./init.sh"))   # runs verify.sh internally

if fails:
    print(f"\n{fails} dimension(s) failed; not clean"); sys.exit(1)
print("\nclean state: all dimensions green")