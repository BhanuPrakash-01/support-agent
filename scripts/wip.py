#!/usr/bin/env python3
"""wip.py — feature_list.json state manager and WIP guard.
Python port of the course's wip.mjs, adapted for support-agent.
Usage: wip.py status | activate <id> | pass <id> | block <id> [reason...]
"""
import json
import subprocess
import sys
from datetime import datetime, timezone

PATH = "feature_list.json"
REQUIRED = ["id", "priority", "area", "title", "user_visible_behavior",
            "verification_command", "scope", "state", "evidence"]
STATES = {"not_started", "in_progress", "blocked", "passing"}

def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)

def load():
    return json.load(open(PATH))

def save(fl):
    open(PATH, "w").write(json.dumps(fl, indent=2) + "\n")

def validate(fl):
    rules = fl.get("rules", {})
    for f in fl["features"]:
        for k in REQUIRED:
            if k not in f:
                fail(f"feature {f.get('id', '?')} missing field: {k}")
        if f["state"] not in STATES:
            fail(f"feature {f['id']} invalid state: {f['state']}")
        if f["state"] == "passing" and rules.get("passing_requires_evidence") and not f["evidence"]:
            fail(f"feature {f['id']} is 'passing' with no evidence; corrupted state.")

def metrics(fl):
    active  = [f for f in fl["features"] if f["state"] == "in_progress"]
    blocked = [f for f in fl["features"] if f["state"] == "blocked"]
    passed  = sum(1 for f in fl["features"] if f["state"] == "passing")
    activated = passed + len(active) + len(blocked)
    vcr = 1.0 if activated == 0 else passed / activated
    return active, blocked, passed, activated, vcr

def find(fl, fid):
    f = next((x for x in fl["features"] if x["id"] == fid), None)
    if f is None:
        fail(f"unknown id: {fid}")
    return f

def main():
    fl = load()
    validate(fl)            # malformed list is always a hard error
    rules = fl.get("rules", {})
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    fid = sys.argv[2] if len(sys.argv) > 2 else None
    active, blocked, passed, activated, vcr = metrics(fl)

    if cmd == "status":
        print(f"active:   {', '.join(f['id'] for f in active) or '(none)'}")
        print(f"blocked:  {', '.join(f['id'] for f in blocked) or '(none)'}")
        print(f"vcr:      {vcr:.2f}  ({passed}/{activated})")

    elif cmd == "activate":
        if not fid:
            fail("activate requires an id")
        wip = rules.get("wip_limit", 1)
        if len(active) >= wip:
            fail(f"WIP={wip}; {active[0]['id']} already active.")
        if vcr < rules.get("vcr_target", 0):
            fail(f"VCR={vcr:.2f} below target; resolve blocked features first.")
        f = find(fl, fid)
        if f["state"] != "not_started":
            fail(f"{fid} is in state '{f['state']}'")
        f["state"] = "in_progress"
        save(fl)
        print(f"activated {fid}")

    elif cmd == "pass":
        if not fid:
            fail("pass requires an id")
        f = find(fl, fid)
        if f["state"] != "in_progress":
            fail(f"{fid} is not in_progress")
        print(f"==> running verification: {f['verification_command']}")
        if subprocess.run(f["verification_command"], shell=True).returncode != 0:
            fail(f"verification failed; {fid} stays in_progress")
        f["state"] = "passing"
        f["evidence"].append({"ts": datetime.now(timezone.utc).isoformat(),
                              "command": f["verification_command"], "exit": 0})
        save(fl)
        print(f"passed {fid}; evidence recorded")

    elif cmd == "block":
        if not fid:
            fail("block requires an id")
        f = find(fl, fid)
        f["state"] = "blocked"
        reason = " ".join(sys.argv[3:])
        if reason:
            f["notes"] = reason
        save(fl)
        print(f"blocked {fid}")

    else:
        fail("usage: wip.py status | activate <id> | pass <id> | block <id> [reason]")

if __name__ == "__main__":
    main()