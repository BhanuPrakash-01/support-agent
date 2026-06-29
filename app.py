import streamlit as st
from support_agent import DB_PATH
from support_agent.agent import handle_ticket
from support_agent.memory import list_customers, get_customer_summary

import os
from support_agent.db_setup import build_database
if not os.path.exists(DB_PATH):
    build_database()

# In the cloud, secrets come from st.secrets; locally they come from .env.
# Copy any st.secrets into environment variables so the rest of the code (which reads
# os.environ) works in both places.
try:
    for key in ["GROQ_API_KEY", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"]:
        if key in st.secrets:
            os.environ[key] = st.secrets[key]
except Exception:
    pass  # no st.secrets locally — that's fine, .env handles it

st.title("Support agent (M1)")
st.caption("Memory-centric support agent with per-customer rolling summaries.")

customers = list_customers()

# Build a friendly label for each customer, mapping back to their id.
label_to_id = {
    f"{name} (ID {cid}, {plan})": cid
    for cid, name, plan in customers
}

choice = st.selectbox("Which customer are you?", list(label_to_id.keys()))
customer_id = label_to_id[choice]

summary = get_customer_summary(customer_id)
if summary:
    with st.expander("Customer summary (read-only)", expanded=True):
        st.write(summary)
else:
    st.caption("No summary on file for this customer yet.")

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