"""Load-bearing tests for M2 retrieval and the agent tool loop.

These are written BEFORE retrieval.py / the loop exist, so on first run they
fail at import — that failure IS the spec. Claude Code implements the API in
the module docstring above until these pass.

Determinism: a stub embedder (keyword bag-of-words) replaces MiniLM, and a stub
model replaces Groq, so nothing here touches the network or downloads a model.
"""
import pytest

from support_agent import retrieval
from support_agent.agent import handle_ticket
from support_agent.memory import close_ticket

# --- deterministic stub embedder -------------------------------------------
_VOCAB = ["billing", "refund", "charge", "crash", "login", "app", "startup", "email"]

def stub_embed(text):
    """Map text to a fixed-length vector by keyword presence. Never all-zero."""
    t = text.lower()
    return [1.0 if w in t else 0.0 for w in _VOCAB] + [0.1]

@pytest.fixture
def col():
    """A fresh, in-memory vector collection per test."""
    return retrieval.make_collection(persist_dir=None)


# === retrieval-001 : search + isolation ====================================

def test_search_returns_relevant(col):
    """search_history ranks the semantically closest past ticket first."""
    retrieval.index_ticket(1, 1001, "billing refund charge dispute", collection=col, embed=stub_embed)
    retrieval.index_ticket(2, 1001, "app crash on startup", collection=col, embed=stub_embed)

    results = retrieval.search_history(1001, "refund charge problem", k=2, collection=col, embed=stub_embed)

    assert results, "search returned nothing"
    assert results[0]["ticket_id"] == 1, "billing ticket should rank above the crash ticket"


def test_search_isolation(col):
    """THE load-bearing test: a customer's search never returns another's tickets,
    even when the other customer's ticket is identical (more 'relevant')."""
    retrieval.index_ticket(10, 1001, "billing refund charge dispute", collection=col, embed=stub_embed)
    retrieval.index_ticket(20, 1002, "billing refund charge dispute", collection=col, embed=stub_embed)  # same text, different owner

    results = retrieval.search_history(1001, "refund charge", k=5, collection=col, embed=stub_embed)

    assert results, "search returned nothing"
    owners = {r["customer_id"] for r in results}
    assert owners == {1001}, f"isolation breach: results include {owners - {1001}}"


# === tool-loop-001 : the model-chosen retrieval loop =======================

def test_loop_executes_tool_call(col):
    """When the model emits a search tool call, the loop runs it, feeds the
    result back, and the model produces a final answer using it."""
    retrieval.index_ticket(1, 1001, "billing refund charge dispute", collection=col, embed=stub_embed)

    state = {"n": 0, "tool_payload": None}
    def stub_model(messages, tools):
        state["n"] += 1
        if state["n"] == 1:  # first turn: ask to search
            return {"content": None, "tool_calls": [
                {"id": "c1", "name": "search_history",
                 "arguments": {"customer_id": 1001, "query": "refund"}}]}
        # second turn: capture what the tool fed back, then answer
        tool_msgs = [m for m in messages if m.get("role") == "tool"]
        state["tool_payload"] = tool_msgs[-1]["content"] if tool_msgs else None
        return {"content": "Here is your refund update.", "tool_calls": None}

    reply = handle_ticket(1001, "where is my refund?", model_call=stub_model,
                          collection=col, embed=stub_embed)

    assert reply == "Here is your refund update.", "loop did not return the final answer"
    assert state["tool_payload"] is not None, "tool result was never fed back to the model"
    assert "refund" in state["tool_payload"].lower(), "retrieved ticket not in the tool result"


def test_loop_terminates(col):
    """A self-contained ticket: the model answers without retrieving, and the
    loop stops after one turn (proves retrieval is model-CHOSEN, not always-on)."""
    state = {"n": 0}
    def stub_model(messages, tools):
        state["n"] += 1
        return {"content": "You can reset your password in Settings.", "tool_calls": None}

    reply = handle_ticket(1001, "how do I reset my password?", model_call=stub_model,
                          collection=col, embed=stub_embed)

    assert reply == "You can reset your password in Settings."
    assert state["n"] == 1, "model answered directly; loop should have run exactly one turn"


def test_loop_respects_max_steps(col):
    """Safety: a model that always asks to search must still terminate (no hang)."""
    retrieval.index_ticket(1, 1001, "billing refund", collection=col, embed=stub_embed)
    state = {"n": 0}
    def runaway_model(messages, tools):
        state["n"] += 1
        return {"content": None, "tool_calls": [
            {"id": f"c{state['n']}", "name": "search_history",
             "arguments": {"customer_id": 1001, "query": "x"}}]}

    handle_ticket(1001, "loop forever?", model_call=runaway_model,
                  collection=col, embed=stub_embed, max_steps=3)

    assert state["n"] == 3, f"loop should cap at max_steps=3, ran {state['n']} times"


# === index-sync-001 : keep the index in sync ===============================

def test_closed_ticket_is_indexed(col):
    """Closing a ticket adds it to the vector index, so it's searchable after."""
    def stub_summarizer(existing, ticket_text):
        return "stub summary"
    # 61450 is customer 1003's open refund ticket in the seed data.
    close_ticket(61450, "Refund processed June 28.",
                 summarizer=stub_summarizer, embed=stub_embed, collection=col)

    results = retrieval.search_history(1003, "refund", k=3, collection=col, embed=stub_embed)
    assert any(r["ticket_id"] == 61450 for r in results), "closed ticket was not indexed"


def test_backfill_indexes_all(col):
    """Backfill indexes every CLOSED ticket; a known closed ticket is findable."""
    retrieval.backfill_index(collection=col, embed=stub_embed)
    # 1001's ticket 55980 ('App crashes on startup') is closed in the seed data.
    results = retrieval.search_history(1001, "crash startup", k=3, collection=col, embed=stub_embed)
    assert any(r["ticket_id"] == 55980 for r in results), "backfill missed a closed ticket"


# === perf-001 : embedder singleton ==========================================

def test_embedder_is_singleton():
    """get_embedder() returns the same object on every call — model loads once."""
    e1 = retrieval.get_embedder()
    e2 = retrieval.get_embedder()
    assert e1 is e2, "embedder must be cached; SentenceTransformer must not reload on second call"