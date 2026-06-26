import sqlite3

conn = sqlite3.connect("support.db")
cur = conn.cursor()

# Pull everything belonging to our repeat customer, 1001.
cur.execute(
    "SELECT ticket_id, subject, status FROM tickets WHERE customer_id = ?",
    (1001,)
)
rows = cur.fetchall()

print("Tickets for customer 1001:")
for r in rows:
    print(" ", r)

conn.close()