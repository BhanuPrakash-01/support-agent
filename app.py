import os
import streamlit as st
from support_agent import DB_PATH
from support_agent.agent import handle_ticket
from support_agent.memory import list_customers, get_customer_summary, close_ticket, get_open_tickets
from support_agent.retrieval import make_collection, get_embedder
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


@st.cache_resource
def _load_embedder():
    """Pre-warm the MiniLM embedder once; survives Streamlit reruns."""
    return get_embedder()


@st.cache_resource
def _load_collection():
    chroma_dir = os.path.join(os.path.dirname(DB_PATH), "chroma")
    return make_collection(persist_dir=chroma_dir)


class _TracingCollection:
    """Proxy that counts how many times search_history queried the collection."""
    def __init__(self, col):
        self._col = col
        self.queries = 0

    def upsert(self, **kw):
        return self._col.upsert(**kw)

    def query(self, **kw):
        self.queries += 1
        return self._col.query(**kw)


_load_embedder()  # warm the singleton before the first user message

st.title("Support agent (M2)")
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
        tracer = _TracingCollection(_load_collection())
        with st.spinner("Agent is thinking..."):
            reply = handle_ticket(customer_id, ticket_message, collection=tracer)
        st.markdown("### Agent reply")
        st.write(reply)
        if tracer.queries > 0:
            st.caption(f"_Retrieval: {tracer.queries} past-ticket search(es) used to inform this reply._")
        else:
            st.caption("_Retrieval: not used — model answered directly from context._")

st.divider()
st.subheader("Close a Ticket")

open_tickets = get_open_tickets(customer_id)

if not open_tickets:
    st.caption("No open tickets for this customer.")
else:
    ticket_options = {f"[#{tid}] {subject}": tid for tid, subject in open_tickets}
    selected_label = st.selectbox("Select open ticket to close:", list(ticket_options.keys()))
    selected_ticket_id = ticket_options[selected_label]

    resolution_text = st.text_area(
        "Resolution:",
        placeholder="Describe how the issue was resolved.",
        key="resolution_input",
    )

    if st.button("Close Ticket"):
        if not resolution_text.strip():
            st.warning("Please enter a resolution before closing.")
        else:
            with st.spinner("Closing ticket and updating customer summary..."):
                close_ticket(
                    selected_ticket_id,
                    resolution_text.strip(),
                    collection=_load_collection(),
                )
            st.success(f"Ticket #{selected_ticket_id} closed. Customer summary updated.")
            st.rerun()
