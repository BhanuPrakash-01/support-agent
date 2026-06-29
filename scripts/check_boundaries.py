#!/usr/bin/env python3
"""check_boundaries.py — static guards for two architectural invariants:
  1. Memory seam  — only memory.py / db_setup.py may import sqlite3.
  2. Isolation    — every SELECT/UPDATE/DELETE on customers|tickets is scoped
                    by a WHERE ... customer_id filter.
Parses the AST so multi-line SQL is checked as a whole statement. A legitimate
all-customer query (e.g. the UI dropdown) is waived with a trailing comment
'# allow: all-customers' on the execute() line.
"""
import ast
import re
import sys
import pathlib

DB_ALLOWED = {"support_agent/memory.py", "support_agent/db_setup.py"}
SCAN       = ["support_agent/memory.py", "support_agent/agent.py",
              "support_agent/db_setup.py", "support_agent/retrieval.py", "app.py"]
TABLE  = re.compile(r"\b(customers|tickets)\b", re.I)
RW     = re.compile(r"\b(select|update|delete)\b", re.I)   # not insert: inserts create rows
SCHEMA = re.compile(r"\b(create|drop|alter)\b", re.I)
SCOPED = re.compile(r"where\b.*customer_id", re.I | re.S)
WAIVER = "allow: all-customers"
violations = 0

def literal_sql(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left_val = literal_sql(node.left)
        right_val = literal_sql(node.right)
        return (left_val + right_val) if (left_val is not None and right_val is not None) else None
    return None

for path in SCAN:
    p = pathlib.Path(path)
    if not p.exists():
        continue
    src = p.read_text()
    lines = src.splitlines()
    tree = ast.parse(src, filename=path)

    if path not in DB_ALLOWED:                       # Boundary 1: the memory seam
        for n in ast.walk(tree):
            mods = ([a.name for a in n.names] if isinstance(n, ast.Import)
                    else [n.module or ""] if isinstance(n, ast.ImportFrom) else [])
            if any(m == "sqlite3" for m in mods):
                print(f"BOUNDARY {path}:{n.lineno}: imports sqlite3 — DB access belongs in memory.py", file=sys.stderr)
                violations += 1

    for n in ast.walk(tree):                          # Boundary 2: isolation
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr in ("execute", "executemany") and n.args):
            sql = literal_sql(n.args[0])
            if not sql or not (TABLE.search(sql) and RW.search(sql)):
                continue
            if SCHEMA.search(sql) or SCOPED.search(sql):
                continue
            if WAIVER in lines[n.lineno - 1]:
                continue
            print(f"ISOLATION {path}:{n.lineno}: customer-table query without a "
                  f"customer_id filter (scope it, or mark '# {WAIVER}')", file=sys.stderr)
            violations += 1

if violations:
    sys.exit(3)
else:
    print("boundaries OK")