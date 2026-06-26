import sqlite3
import streamlit as st
from agent import handle_ticket

import os
if not os.path.exists("support.db"):
    import db_setup  # running the import builds the database

# In the cloud, secrets come from st.secrets; locally they come from .env.
# Copy any st.secrets into environment variables so the rest of the code (which reads
# os.environ) works in both places.
try:
    for key in ["GROQ_API_KEY", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"]:
        if key in st.secrets:
            os.environ[key] = st.secrets[key]
except Exception:
    pass  # no st.secrets locally — that's fine, .env handles it

DB_PATH = "support.db"

def get_all_customers():
    """Fetch (id, name, plan) for every customer, to populate the dropdown."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT customer_id, name, plan FROM customers ORDER BY customer_id")
    rows = cur.fetchall()
    conn.close()
    return rows

st.title("Support agent (M0)")
st.caption("A walking-skeleton support agent with primitive memory.")

customers = get_all_customers()

# Build a friendly label for each customer, mapping back to their id.
label_to_id = {
    f"{name} (ID {cid}, {plan})": cid
    for cid, name, plan in customers
}

choice = st.selectbox("Which customer are you?", list(label_to_id.keys()))
customer_id = label_to_id[choice]

ticket_message = st.text_area(
    "Describe your issue:",
    placeholder="e.g. The app is crashing again when I open it.",
)

if st.button("Send to support agent"):
    if not ticket_message.strip():
        st.warning("Please type a message first.")
    else:
        with st.spinner("Agent is thinking..."):
            reply = handle_ticket(customer_id, ticket_message)
        st.markdown("### Agent reply")
        st.write(reply)