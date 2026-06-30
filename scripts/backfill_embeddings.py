#!/usr/bin/env python3
"""Backfill the vector index with all existing CLOSED tickets.

Idempotent: re-running does not create duplicate entries (upsert by ticket_id).
Run once after deploying retrieval-001, or whenever the index needs rebuilding.

Usage:
    python scripts/backfill_embeddings.py
"""
import sys
import os

# Allow running from the project root without `pip install -e .` in the path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from support_agent.retrieval import make_collection, backfill_index

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "chroma")

if __name__ == "__main__":
    col = make_collection(persist_dir=DATA_DIR)
    print(f"Indexing closed tickets into {DATA_DIR} ...")
    backfill_index(collection=col)
    print("Done.")
