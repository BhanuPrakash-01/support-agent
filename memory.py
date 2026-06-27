import sqlite3

DB_PATH = "support.db"

def get_customer_context(customer_id: int) -> str:
    """Return a plain-text summary of a customer and their ticket history.
    This is the M0 'memory': a dumb fetch-and-format, no retrieval or summarization.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1) Who is this customer?
    cur.execute(
        "SELECT name, plan, created_at FROM customers WHERE customer_id = ?",
        (customer_id,),
    )
    customer = cur.fetchone()

    if customer is None:
        conn.close()
        return f"No customer found with id {customer_id}."

    name, plan, created_at = customer

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


def get_all_customers():
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