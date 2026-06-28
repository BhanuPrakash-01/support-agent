import sqlite3
conn = sqlite3.connect("support.db")
for cid, name, summary in conn.execute(
    "SELECT customer_id, name, summary FROM customers"
):
    print(cid, name, "->", repr(summary))