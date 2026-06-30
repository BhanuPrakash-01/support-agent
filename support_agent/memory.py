import sqlite3
from support_agent import DB_PATH


def get_customer_context(customer_id: int) -> str:
    """Return a plain-text summary of a customer and their ticket history.
    This is the M0 'memory': a dumb fetch-and-format, no retrieval or summarization.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1) Who is this customer?
    cur.execute(
        "SELECT name, plan, created_at, summary FROM customers WHERE customer_id = ?",
        (customer_id,),
    )
    customer = cur.fetchone()

    if customer is None:
        conn.close()
        return f"No customer found with id {customer_id}."

    name, plan, created_at, summary = customer

    # 2) What have they contacted us about before? Newest first.
    cur.execute(
        """SELECT subject, status, resolution, created_at
           FROM tickets
           WHERE customer_id = ?
           ORDER BY created_at DESC""",
        (customer_id,),
    )
    tickets = cur.fetchall()
    conn.close()

    # 3) Format it all into a readable block of text.
    lines = []
    if summary:
        lines.append(f"Profile summary: {summary}")
        lines.append("")
    lines.append(f"Customer: {name} (ID {customer_id})")
    lines.append(f"Plan: {plan}, customer since {created_at}")

    if not tickets:
        lines.append("Past tickets: none. This is their first contact.")
    else:
        lines.append(f"Past tickets ({len(tickets)} total), most recent first:")
        for subject, status, resolution, created in tickets:
            resolved = resolution if resolution else "not yet resolved"
            lines.append(f"  - [{created}] {subject} (status: {status}) — {resolved}")

    return "\n".join(lines)


def _default_summarizer(existing_summary, ticket_text):
    """Real summarizer: calls Groq with retry-on-429."""
    import os
    import time
    from dotenv import load_dotenv
    from openai import OpenAI, RateLimitError
    load_dotenv()
    client = OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
    )
    prior = f"Existing summary:\n{existing_summary}\n\n" if existing_summary else ""
    prompt = (
        f"{prior}New closed ticket:\n{ticket_text}\n\n"
        "Write a customer profile summary in at most 3 sentences.\n"
        "Rules:\n"
        "- Use only facts stated in the tickets; do not invent sentiment or outcomes.\n"
        "- Do NOT include the customer's name or plan (those are stored separately).\n"
        "- Never write 'Unknown', '[Not specified]', or any placeholder for missing data.\n"
        "- If a fact is absent, omit it entirely rather than substituting a placeholder.\n"
        "- Be specific and grounded: mention issue types and resolutions that actually appear in the tickets."
    )
    for attempt in range(4):
        try:
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content.strip()
        except RateLimitError:
            time.sleep(2 ** attempt)
    raise RuntimeError("Still rate limited after retries.")


def update_customer_summary(customer_id: int, ticket: dict, summarizer=None) -> None:
    """Fold a closed ticket into the customer's rolling summary and persist it."""
    if summarizer is None:
        summarizer = _default_summarizer

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT summary FROM customers WHERE customer_id = ?",
        (customer_id,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return  # unknown customer — nothing to update

    existing = row[0]  # may be None

    ticket_text = (
        f"Subject: {ticket.get('subject', '')}\n"
        f"Body: {ticket.get('body', '')}\n"
        f"Resolution: {ticket.get('resolution', '')}"
    )
    new_summary = summarizer(existing, ticket_text)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE customers SET summary = ? WHERE customer_id = ?",
        (new_summary, customer_id),
    )
    conn.commit()
    conn.close()


def close_ticket(ticket_id: int, resolution: str, summarizer=None) -> None:
    """Mark a ticket Closed, persist the resolution, and fold it into the customer's summary."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT customer_id, subject, body FROM tickets WHERE ticket_id = ?",
        (ticket_id,),
    )
    row = cur.fetchone()
    if row is None:
        conn.close()
        return
    customer_id, subject, body = row
    cur.execute(
        "UPDATE tickets SET status = 'Closed', resolution = ? WHERE ticket_id = ?",
        (resolution, ticket_id),
    )
    conn.commit()
    conn.close()
    update_customer_summary(
        customer_id,
        {"subject": subject, "body": body, "resolution": resolution},
        summarizer=summarizer,
    )


def get_customer_summary(customer_id: int):
    """Return the stored summary string for a customer, or None if absent."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT summary FROM customers WHERE customer_id = ?",
        (customer_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def backfill_summaries(summarizer=None) -> None:
    """Idempotent: reset every customer summary to NULL, then fold in their CLOSED tickets."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE customers SET summary = NULL")  # allow: all-customers
    conn.commit()
    conn.close()

    for customer_id, _name, _plan in list_customers():
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """SELECT subject, body, resolution FROM tickets
               WHERE customer_id = ? AND status = 'Closed'
               ORDER BY created_at ASC""",
            (customer_id,),
        )
        closed_tickets = cur.fetchall()
        conn.close()
        for subject, body, resolution in closed_tickets:
            update_customer_summary(
                customer_id,
                {"subject": subject, "body": body, "resolution": resolution},
                summarizer=summarizer,
            )


def get_open_tickets(customer_id: int) -> list:
    """Return [(ticket_id, subject), ...] for all Open tickets belonging to customer_id."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT ticket_id, subject FROM tickets"
        " WHERE customer_id = ? AND status = 'Open'"
        " ORDER BY created_at DESC",
        (customer_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_customers():
    """Fetch (id, name, plan) for every customer, to populate the dropdown."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT customer_id, name, plan FROM customers ORDER BY customer_id")  # allow: all-customers
    rows = cur.fetchall()
    conn.close()
    return rows


# Quick manual test when run directly.
if __name__ == "__main__":
    print("--- Repeat customer (1001) ---")
    print(get_customer_context(1001))
    print()
    print("--- First-timer (1002) ---")
    print(get_customer_context(1002))
    print()
    print("--- Unknown customer (9999) ---")
    print(get_customer_context(9999))