#!/usr/bin/env python3
"""One-time backfill: fold all closed seed tickets into customer summaries.
Run from the project root: python3 scripts/backfill_summaries.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory import backfill_summaries

if __name__ == "__main__":
    backfill_summaries()
    print("Backfill complete.")
