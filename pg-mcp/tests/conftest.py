"""Pytest configuration and shared fixtures.

This module provides shared fixtures and configuration for all tests.
"""

import os
from typing import Any

import pytest

from pg_mcp.config.settings import (
    CacheConfig,
    DatabaseConfig,
    ObservabilityConfig,
    OpenAIConfig,
    ResilienceConfig,
    SecurityConfig,
    Settings,
    ValidationConfig,
    reset_settings,
)
from pg_mcp.models.schema import ColumnSchema, DatabaseSchema, TableSchema
from pg_mcp.resilience.circuit_breaker import CircuitBreaker
from pg_mcp.resilience.rate_limiter import MultiRateLimiter
from tests.mocks.openai_mock import MockOpenAIClient
from tests.mocks.postgres_mock import MockPostgresPool


@pytest.fixture(autouse=True)
def reset_config() -> None:
    """Reset global settings before each test."""
    reset_settings()


@pytest.fixture(autouse=True)
def disable_metrics_for_tests():
    """Disable metrics for tests to avoid port conflicts."""
    os.environ["OBSERVABILITY_METRICS_ENABLED"] = "false"
    yield
    # Clean up
    if "OBSERVABILITY_METRICS_ENABLED" in os.environ:
        del os.environ["OBSERVABILITY_METRICS_ENABLED"]


# Mock fixtures for testing


@pytest.fixture
def mock_openai() -> MockOpenAIClient:
    """Provide a mock OpenAI client for testing.

    Returns:
        MockOpenAIClient instance with default responses.
    """
    client = MockOpenAIClient()
    # Set some common default responses
    client.set_response("count", "SELECT COUNT(*) FROM users")
    client.set_response("total", "SELECT SUM(amount) FROM orders")
    client.set_response("average", "SELECT AVG(price) FROM products")
    return client


@pytest.fixture
def mock_postgres_pool() -> MockPostgresPool:
    """Provide a mock PostgreSQL connection pool for testing.

    Returns:
        MockPostgresPool instance with common query results.
    """
    pool = MockPostgresPool()

    # Set common query results
    pool.set_query_result(
        "SELECT * FROM users",
        [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
        ],
    )

    pool.set_query_result(
        "SELECT COUNT(*) FROM users",
        [{"count": 2}],
    )

    pool.set_query_result(
        "SELECT * FROM orders",
        [
            {"id": 1, "user_id": 1, "amount": 100.50, "status": "completed"},
            {"id": 2, "user_id": 2, "amount": 250.00, "status": "pending"},
        ],
    )

    pool.set_query_result(
        "SELECT SUM(amount) FROM orders",
        [{"sum": 350.50}],
    )

    # Schema introspection queries
    pool.set_query_result(
        "SELECT table_name FROM information_schema.tables",
        [
            {"table_name": "users"},
            {"table_name": "orders"},
            {"table_name": "products"},
        ],
    )

    pool.set_query_result(
        "SELECT column_name, data_type FROM information_schema.columns",
        [
            {"column_name": "id", "data_type": "integer"},
            {"column_name": "name", "data_type": "text"},
            {"column_name": "email", "data_type": "text"},
        ],
    )

    return pool


@pytest.fixture
def mock_settings() -> Settings:
    """Provide mock settings for testing.

    Returns:
        Settings instance with test-friendly defaults.
    """
    return Settings(
        environment="development",
        database=DatabaseConfig(
            host="localhost",
            port=5432,
            name="test_db",
            user="test_user",
            password="test_password",
            min_pool_size=1,
            max_pool_size=5,
            pool_timeout=5.0,
            command_timeout=5.0,
        ),
        openai=OpenAIConfig(
            api_key="sk-test-key-not-real",
            model="gpt-4o-mini",
            max_tokens=1000,
            temperature=0.0,
            timeout=10.0,
        ),
        security=SecurityConfig(
            allow_write_operations=False,
            blocked_functions=["pg_sleep", "pg_read_file"],
            max_rows=1000,
            max_execution_time=10.0,
            blocked_tables=[],
            blocked_columns={},
            allow_explain=True,
            require_where_clause=[],
            max_join_tables=10,
        ),
        validation=ValidationConfig(
            max_question_length=5000,
            min_confidence_score=70,
            enabled=True,
            sample_rows=5,
            timeout_seconds=10.0,
            confidence_threshold=70,
        ),
        cache=CacheConfig(
            schema_ttl=3600,
            max_size=100,
            enabled=True,
        ),
        resilience=ResilienceConfig(
            max_retries=2,
            retry_delay=0.1,
            backoff_factor=2.0,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=5.0,
        ),
        observability=ObservabilityConfig(
            metrics_enabled=False,
            metrics_port=9090,
            log_level="INFO",
            log_format="text",
        ),
    )


@pytest.fixture
def mock_circuit_breaker() -> CircuitBreaker:
    """Provide a mock circuit breaker for testing.

    Returns:
        CircuitBreaker instance configured for testing.
    """
    return CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=5.0,
    )


@pytest.fixture
def mock_rate_limiter() -> MultiRateLimiter:
    """Provide a mock rate limiter for testing.

    Returns:
        MultiRateLimiter instance configured for testing.
    """
    return MultiRateLimiter(
        query_limit=100,  # High limit for tests
        llm_limit=50,
    )


@pytest.fixture
def mock_schema() -> DatabaseSchema:
    """Provide a mock database schema for testing.

    Returns:
        DatabaseSchema with common test tables.
    """
    return DatabaseSchema(
        database_name="test_db",
        tables=[
            TableSchema(
                name="users",
                columns=[
                    ColumnSchema(
                        name="id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=True,
                        column_default="nextval('users_id_seq'::regclass)",
                        description="User ID",
                    ),
                    ColumnSchema(
                        name="name",
                        data_type="text",
                        is_nullable=False,
                        is_primary_key=False,
                        column_default=None,
                        description="User name",
                    ),
                    ColumnSchema(
                        name="email",
                        data_type="text",
                        is_nullable=False,
                        is_primary_key=False,
                        column_default=None,
                        description="User email",
                    ),
                    ColumnSchema(
                        name="created_at",
                        data_type="timestamp",
                        is_nullable=False,
                        is_primary_key=False,
                        column_default="now()",
                        description="Creation timestamp",
                    ),
                ],
                row_count=100,
                description="User accounts",
            ),
            TableSchema(
                name="orders",
                columns=[
                    ColumnSchema(
                        name="id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=True,
                        column_default="nextval('orders_id_seq'::regclass)",
                        description="Order ID",
                    ),
                    ColumnSchema(
                        name="user_id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=False,
                        column_default=None,
                        description="User ID (foreign key)",
                    ),
                    ColumnSchema(
                        name="amount",
                        data_type="numeric",
                        is_nullable=False,
                        is_primary_key=False,
                        column_default=None,
                        description="Order amount",
                    ),
                    ColumnSchema(
                        name="status",
                        data_type="text",
                        is_nullable=False,
                        is_primary_key=False,
                        column_default="'pending'::text",
                        description="Order status",
                    ),
                ],
                row_count=500,
                description="Customer orders",
            ),
            TableSchema(
                name="products",
                columns=[
                    ColumnSchema(
                        name="id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=True,
                        column_default="nextval('products_id_seq'::regclass)",
                        description="Product ID",
                    ),
                    ColumnSchema(
                        name="name",
                        data_type="text",
                        is_nullable=False,
                        is_primary_key=False,
                        column_default=None,
                        description="Product name",
                    ),
                    ColumnSchema(
                        name="price",
                        data_type="numeric",
                        is_nullable=False,
                        is_primary_key=False,
                        column_default=None,
                        description="Product price",
                    ),
                    ColumnSchema(
                        name="category",
                        data_type="text",
                        is_nullable=True,
                        is_primary_key=False,
                        column_default=None,
                        description="Product category",
                    ),
                ],
                row_count=200,
                description="Product catalog",
            ),
        ],
    )
