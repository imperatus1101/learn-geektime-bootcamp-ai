"""
Test configuration and fixtures for export functionality tests.
"""

import pytest
from sqlmodel import create_engine, Session, SQLModel
from app.models.export import QueryExport
from app.models.database import DatabaseConnection


@pytest.fixture(scope="function")
def test_db_session():
    """
    Create a test database session with all required tables.

    This fixture creates an in-memory SQLite database for testing.
    Each test gets a fresh database instance.
    """
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:")

    # Create all tables
    SQLModel.metadata.create_all(engine)

    # Create session
    with Session(engine) as session:
        yield session

        # Cleanup happens automatically when context exits


@pytest.fixture(scope="function")
def sample_export_data():
    """
    Provide sample data for export tests.

    Returns a tuple of (columns, rows) that can be used in export tests.
    """
    columns = [
        {"name": "id", "dataType": "integer"},
        {"name": "name", "dataType": "varchar"},
        {"name": "email", "dataType": "varchar"},
        {"name": "active", "dataType": "boolean"},
    ]

    rows = [
        {"id": 1, "name": "Alice", "email": "alice@example.com", "active": True},
        {"id": 2, "name": "Bob", "email": "bob@example.com", "active": False},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com", "active": True},
    ]

    return columns, rows


@pytest.fixture(scope="function")
def large_export_data():
    """
    Provide large dataset for performance testing.

    Returns a tuple of (columns, rows) with 1000 rows.
    """
    columns = [
        {"name": "id", "dataType": "integer"},
        {"name": "name", "dataType": "varchar"},
        {"name": "value", "dataType": "numeric"},
    ]

    rows = [
        {
            "id": i,
            "name": f"User {i}",
            "value": i * 1.5,
        }
        for i in range(1000)
    ]

    return columns, rows


@pytest.fixture(scope="function")
def special_chars_data():
    """
    Provide data with special characters for edge case testing.
    """
    columns = [
        {"name": "id", "dataType": "integer"},
        {"name": "text", "dataType": "varchar"},
    ]

    rows = [
        {"id": 1, "text": "Hello, World!"},
        {"id": 2, "text": 'Quote: "test"'},
        {"id": 3, "text": "Newline:\ntest"},
        {"id": 4, "text": "Tab:\ttest"},
        {"id": 5, "text": "中文测试"},
        {"id": 6, "text": "Special: @#$%^&*()"},
        {"id": 7, "text": "O'Brien"},  # Single quote
        {"id": 8, "text": "NULL"},
    ]

    return columns, rows


# Async fixtures
@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for async tests.

    This is needed for pytest-asyncio to work properly.
    """
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
