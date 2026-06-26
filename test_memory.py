"""Minimal eval seed for M0. Grows into the real harness in later milestones."""
from memory import get_customer_context

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

if __name__ == "__main__":
    test_context_includes_past_tickets()
    test_isolation_between_customers()
    test_unknown_customer_is_handled()
    print("All M0 eval checks passed.")