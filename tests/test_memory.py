"""Minimal eval seed for M0. Grows into the real harness in later milestones."""
import sqlite3
from support_agent import DB_PATH
from support_agent.memory import get_customer_context, update_customer_summary, close_ticket, backfill_summaries


def test_customers_has_summary_column():
    """The customers table must have a nullable summary TEXT column."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(customers)")
    columns = {row[1]: row[2] for row in cur.fetchall()}
    conn.close()
    assert "summary" in columns, "summary column missing from customers table"
    assert columns["summary"].upper() == "TEXT", f"expected TEXT, got {columns['summary']}"

def test_summary_update_first_time():
    """update_customer_summary works when no prior summary exists (NULL case)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE customers SET summary = NULL WHERE customer_id = 1001")
    conn.commit()
    conn.close()

    def stub(existing, ticket_text):
        return "First-time stub summary."
    update_customer_summary(
        1001,
        {"subject": "Test", "body": "Body text", "resolution": "Fixed"},
        summarizer=stub,
    )

    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT summary FROM customers WHERE customer_id = 1001").fetchone()
    conn.close()
    assert row[0] is not None, "summary should not be None after first update"
    assert len(row[0]) > 0, "summary should be non-empty"


def test_summary_update_persists():
    """update_customer_summary persists the stub's output and stays within the word bound."""
    stub_text = " ".join(["word"] * 50)  # 50 words — well under the 120-word cap
    def stub(existing, ticket_text):
        return stub_text
    update_customer_summary(
        1001,
        {"subject": "Crash", "body": "App crash on launch", "resolution": "Patched in 4.2.1"},
        summarizer=stub,
    )

    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT summary FROM customers WHERE customer_id = 1001").fetchone()
    conn.close()
    persisted = row[0]
    assert persisted is not None, "summary was not persisted"
    assert len(persisted) > 0, "summary is empty"
    assert len(persisted.split()) <= 120, f"summary too long: {len(persisted.split())} words"


def test_close_ticket_persists():
    """close_ticket marks the ticket Closed and triggers a summary update for the owner."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE tickets SET status = 'Open', resolution = NULL WHERE ticket_id = 61450")
    conn.execute("UPDATE customers SET summary = NULL WHERE customer_id = 1003")
    conn.commit()
    conn.close()

    def stub(existing, ticket_text):
        return "Customer 1003 stub summary."
    close_ticket(61450, "Refund processed", summarizer=stub)

    conn = sqlite3.connect(DB_PATH)
    ticket_row = conn.execute(
        "SELECT status, resolution FROM tickets WHERE ticket_id = 61450"
    ).fetchone()
    summary_row = conn.execute(
        "SELECT summary FROM customers WHERE customer_id = 1003"
    ).fetchone()
    conn.close()

    assert ticket_row[0] == "Closed", f"expected Closed, got {ticket_row[0]}"
    assert ticket_row[1] == "Refund processed", "resolution not stored"
    assert summary_row[0] is not None, "customer 1003 summary not updated"
    assert len(summary_row[0]) > 0, "customer 1003 summary is empty"


def test_close_ticket_isolation():
    """Closing customer 1003's ticket must not touch customer 1002's summary."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE customers SET summary = 'sentinel-1002' WHERE customer_id = 1002")
    conn.execute("UPDATE tickets SET status = 'Open', resolution = NULL WHERE ticket_id = 61450")
    conn.commit()
    conn.close()

    def stub(existing, ticket_text):
        return "Updated 1003 summary."
    close_ticket(61450, "Resolved", summarizer=stub)

    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT summary FROM customers WHERE customer_id = 1002"
    ).fetchone()
    conn.close()
    assert row[0] == "sentinel-1002", f"isolation breach: 1002's summary changed to {row[0]!r}"


def test_summary_injected():
    """When a summary exists it appears at the top of the context, above the ticket list."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE customers SET summary = 'Known test summary text.' WHERE customer_id = 1001")
    conn.commit()
    conn.close()

    context = get_customer_context(1001)
    assert "Known test summary text." in context, "summary not present in context"
    summary_pos = context.index("Known test summary text.")
    ticket_pos = context.index("Past tickets")
    assert summary_pos < ticket_pos, "summary should appear before the ticket list"


def test_no_summary_renders():
    """When summary is absent the context renders cleanly — no 'None', no crash."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE customers SET summary = NULL WHERE customer_id = 1001")
    conn.commit()
    conn.close()

    context = get_customer_context(1001)
    assert "None" not in context, "literal 'None' must not appear in context"
    assert "ID 1001" in context, "customer identity missing when summary is absent"


def test_backfill_excludes_open_tickets():
    """Backfill must not fold open tickets; customer with only open tickets stays NULL."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE tickets SET status = 'Open', resolution = NULL WHERE ticket_id = 61450")
    conn.execute("UPDATE customers SET summary = NULL")
    conn.commit()
    conn.close()

    def stub(existing, ticket_text):
        return "backfilled"
    backfill_summaries(summarizer=stub)

    conn = sqlite3.connect(DB_PATH)
    rows = {
        r[0]: r[1]
        for r in conn.execute("SELECT customer_id, summary FROM customers").fetchall()
    }
    conn.close()

    assert rows[1001] is not None, "1001 has 3 closed tickets — summary should be set"
    assert rows[1002] is not None, "1002 has 1 closed ticket — summary should be set"
    assert rows[1003] is None, "1003 has only an open ticket — summary must remain NULL"


def test_backfill_idempotent():
    """Running backfill twice produces the same summary as running it once."""
    counter = {"n": 0}

    def stub(existing, ticket_text):
        counter["n"] += 1
        return f"summary-{counter['n']}"

    backfill_summaries(summarizer=stub)
    conn = sqlite3.connect(DB_PATH)
    after_first = conn.execute(
        "SELECT customer_id, summary FROM customers ORDER BY customer_id"
    ).fetchall()
    conn.close()

    counter["n"] = 0
    backfill_summaries(summarizer=stub)
    conn = sqlite3.connect(DB_PATH)
    after_second = conn.execute(
        "SELECT customer_id, summary FROM customers ORDER BY customer_id"
    ).fetchall()
    conn.close()

    assert after_first == after_second, "backfill is not idempotent"


def test_context_includes_past_tickets():
    """The repeat customer's context must surface their prior ticket subjects."""
    context = get_customer_context(1001)
    assert "App crashes on startup" in context, "Missing a known past ticket subject"
    assert "Billing charged twice" in context, "Missing a known past ticket subject"
    assert "ID 1001" in context, "Customer identity missing from context"

def test_isolation_between_customers():
    """Customer 1002's context must NOT contain customer 1001's tickets."""
    context = get_customer_context(1002)
    assert "App crashes on startup" not in context, "Isolation breach: 1001's ticket leaked into 1002"

def test_unknown_customer_is_handled():
    """An unknown id should not crash; it returns a clear message."""
    context = get_customer_context(9999)
    assert "No customer found" in context

def test_summary_bounded():
    """Summary stored by update_customer_summary must be at most 3 sentences."""
    three_sentences = (
        "Customer has reported recurring login failures across multiple sessions. "
        "Two tickets were resolved via password resets. "
        "One billing dispute was refunded after review."
    )

    def stub(existing, ticket_text):
        return three_sentences

    update_customer_summary(
        1001,
        {"subject": "Login", "body": "Cannot log in", "resolution": "Reset password"},
        summarizer=stub,
    )

    conn = sqlite3.connect(DB_PATH)
    summary = conn.execute(
        "SELECT summary FROM customers WHERE customer_id = 1001"
    ).fetchone()[0]
    conn.close()

    assert summary is not None, "summary should not be None"
    sentences = [s.strip() for s in summary.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    assert len(sentences) <= 3, f"expected <= 3 sentences, got {len(sentences)}: {summary!r}"


def test_summary_no_unknown_placeholders():
    """Stored summary must not contain 'Unknown' or '[Not specified]'."""
    clean_summary = (
        "Customer experienced billing overcharges on two occasions. "
        "Both issues were resolved with full refunds."
    )

    def stub(existing, ticket_text):
        return clean_summary

    update_customer_summary(
        1001,
        {"subject": "Billing", "body": "Charged twice", "resolution": "Refunded"},
        summarizer=stub,
    )

    conn = sqlite3.connect(DB_PATH)
    summary = conn.execute(
        "SELECT summary FROM customers WHERE customer_id = 1001"
    ).fetchone()[0]
    conn.close()

    assert summary is not None, "summary should not be None"
    assert "Unknown" not in summary, f"'Unknown' found in summary: {summary!r}"
    assert "[Not specified]" not in summary, f"'[Not specified]' found in summary: {summary!r}"


if __name__ == "__main__":
    test_context_includes_past_tickets()
    test_isolation_between_customers()
    test_unknown_customer_is_handled()
    print("All M0 eval checks passed.")