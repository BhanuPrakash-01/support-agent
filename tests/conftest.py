"""Shared fixtures. Ensures every test session runs against a freshly built DB."""
import pytest
from support_agent.db_setup import build_database

@pytest.fixture(scope="session", autouse=True)
def fresh_db():
    build_database()
    yield