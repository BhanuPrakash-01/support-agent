import sqlite3
from support_agent import DB_PATH
conn = sqlite3.connect(DB_PATH)
for cid, name, summary in conn.execute(
    "SELECT customer_id, name, summary FROM customers"
):
    print(cid, name, "->", repr(summary))