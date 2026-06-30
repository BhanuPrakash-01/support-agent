"""
Episodic retrieval for the support agent.

Public API
----------
make_collection(persist_dir=None) -> chromadb.Collection
    Return a Chroma collection backed by disk (persist_dir given) or in-memory
    (persist_dir=None). Single shared collection named "tickets".

index_ticket(ticket_id, customer_id, text, *, collection, embed=None) -> None
    Embed `text` and upsert it with {ticket_id, customer_id} in metadata.
    Uses ticket_id as the document ID so re-indexing is idempotent.

search_history(customer_id, query, k=4, *, collection, embed=None) -> list[dict]
    Embed `query`, query the collection with where={"customer_id": customer_id},
    and return up to k results as [{"ticket_id": int, "customer_id": int, "text": str}, ...].
    ISOLATION INVARIANT: the where-filter is non-negotiable.

backfill_index(*, collection, embed=None) -> None
    Read every CLOSED ticket from the DB and index it. Idempotent (upsert).
"""

import warnings

import chromadb

# Silence noisy UserWarnings from torch and sentence-transformers at import time.
warnings.filterwarnings("ignore", category=UserWarning, module=r"torch")
warnings.filterwarnings("ignore", category=UserWarning, module=r"sentence_transformers")
warnings.filterwarnings("ignore", category=FutureWarning, module=r"transformers")

COLLECTION_NAME = "tickets"

_embedder = None  # module-level singleton; loaded once on first use


def get_embedder():
    """Return the shared MiniLM embedder, loading it on the first call only."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _default_embed(text: str) -> list:
    return get_embedder().encode(text).tolist()


def make_collection(persist_dir=None):
    """Return a Chroma collection; ephemeral when persist_dir is None."""
    if persist_dir is None:
        client = chromadb.EphemeralClient()
    else:
        client = chromadb.PersistentClient(path=persist_dir)
    return client.get_or_create_collection(COLLECTION_NAME)


def index_ticket(ticket_id: int, customer_id: int, text: str, *, collection, embed=None) -> None:
    """Embed text and upsert into the collection with customer_id in metadata."""
    if embed is None:
        embed = _default_embed
    vector = embed(text)
    collection.upsert(
        ids=[str(ticket_id)],
        embeddings=[vector],
        metadatas=[{"ticket_id": ticket_id, "customer_id": customer_id}],
        documents=[text],
    )


def search_history(customer_id: int, query: str, k: int = 4, *, collection, embed=None) -> list:
    """Return up to k past tickets for customer_id most relevant to query.

    ISOLATION: every query passes where={'customer_id': customer_id}.
    """
    if embed is None:
        embed = _default_embed
    vector = embed(query)
    results = collection.query(
        query_embeddings=[vector],
        n_results=k,
        where={"customer_id": customer_id},
    )
    output = []
    metas = results.get("metadatas", [[]])[0]
    docs = results.get("documents", [[]])[0]
    for i, meta in enumerate(metas):
        output.append({
            "ticket_id": meta["ticket_id"],
            "customer_id": meta["customer_id"],
            "text": docs[i],
        })
    return output


def backfill_index(*, collection, embed=None) -> None:
    """Index all CLOSED tickets from the DB into the collection. Idempotent via upsert."""
    from support_agent.memory import get_closed_tickets
    for ticket_id, customer_id, subject, body, resolution in get_closed_tickets():
        text = f"{subject}\n{body}\nResolution: {resolution or ''}"
        index_ticket(ticket_id, customer_id, text, collection=collection, embed=embed)
