import os
import sqlite3
from support_agent import DB_PATH

def build_database():

    # Connecting to a file that doesn't exist yet creates it.
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Start clean every time we run this script, so re-running is safe.
    cur.execute("DROP TABLE IF EXISTS tickets")
    cur.execute("DROP TABLE IF EXISTS customers")

    cur.execute("""
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        name        TEXT NOT NULL,
        plan        TEXT NOT NULL,
        created_at  TEXT NOT NULL,
        summary     TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE tickets (
        ticket_id   INTEGER PRIMARY KEY,
        customer_id INTEGER NOT NULL,
        subject     TEXT NOT NULL,
        body        TEXT NOT NULL,
        status      TEXT NOT NULL,
        resolution  TEXT,
        created_at  TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    )
    """)

    # --- Seed data: 3 customers ---
    customers = [
        (1001, "Asha Verma",  "Premium", "2025-01-12"),
        (1002, "Ravi Nair",   "Free",    "2026-05-30"),
        (1003, "Meera Das",   "Pro",     "2025-09-03"),
    ]
    cur.executemany(
        "INSERT INTO customers (customer_id, name, plan, created_at) VALUES (?, ?, ?, ?)", customers
    )

    # --- Seed data: tickets ---
    # 1001 is our REPEAT customer (3 past tickets) — the demo account.
    # 1002 and 1003 each have one, so most customers look "normal".
    tickets = [
        (48217, 1001, "Login fails on mobile app",
        "I can't log in from the Android app, keeps saying invalid password.",
        "Closed", "Reset auth token; cleared app cache. Resolved.", "2026-02-10"),
        (51120, 1001, "Billing charged twice",
        "I was charged twice for my March subscription.",
        "Closed", "Refunded duplicate charge of the March cycle.", "2026-03-15"),
        (55980, 1001, "App crashes on startup",
        "After the latest update the app closes immediately when I open it.",
        "Closed", "Guided rollback to previous version; bug fixed in 4.2.1.", "2026-05-02"),
        (60013, 1002, "How do I change my email?",
        "I want to update the email on my account.",
        "Closed", "Sent steps to update email under Account settings.", "2026-06-01"),
        (61450, 1003, "Refund not received",
        "I requested a refund last week and haven't seen it.",
        "Open", None, "2026-06-20"),
    ]
    cur.executemany(
        "INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?)", tickets
    )

    conn.commit()
    conn.close()
    print(f"Database created: {DB_PATH}")


if __name__ == "__main__":
    build_database()