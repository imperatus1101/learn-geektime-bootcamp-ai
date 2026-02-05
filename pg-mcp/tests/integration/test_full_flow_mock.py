"""Integration tests using mock dependencies.

This module tests the complete query flow using mock implementations
of external services, ensuring deterministic and offline testing.
"""

import pytest

from pg_mcp.cache.schema_cache import SchemaCache
from pg_mcp.models.query import QueryRequest, QueryResponse, ReturnType
from pg_mcp.services.orchestrator import QueryOrchestrator
from pg_mcp.services.result_validator import ResultValidator
from pg_mcp.services.sql_executor import ExecutorManager, SQLExecutor
from pg_mcp.services.sql_generator import SQLGenerator
from pg_mcp.services.sql_validator import SQLValidator


@pytest.mark.asyncio
class TestFullQueryFlowWithMocks:
    """Test complete query flow using mocks."""

    async def test_successful_query_flow(
        self,
        mock_openai,
        mock_postgres_pool,
        mock_settings,
        mock_circuit_breaker,
        mock_rate_limiter,
        mock_schema,
    ):
        """Test successful end-to-end query execution with mocks."""
        # Setup: Configure mock responses
        mock_openai.set_response(
            "how many users",
            "SELECT COUNT(*) FROM users",
        )

        # Create components
        sql_generator = SQLGenerator(mock_settings.openai)
        sql_generator._client = mock_openai  # Inject mock client

        sql_validator = SQLValidator(
            config=mock_settings.security,
        )

        executor = SQLExecutor(
            pool=mock_postgres_pool,
            security_config=mock_settings.security,
            db_config=mock_settings.database,
        )

        executor_manager = ExecutorManager(
            executors={"test_db": executor},
            default_database="test_db",
        )

        result_validator = ResultValidator(
            openai_config=mock_settings.openai,
            validation_config=mock_settings.validation,
        )
        result_validator._client = mock_openai  # Inject mock client

        # Create schema cache with mock schema
        schema_cache = SchemaCache(mock_settings.cache)
        schema_cache._cache["test_db"] = mock_schema

        # Create orchestrator
        orchestrator = QueryOrchestrator(
            sql_generator=sql_generator,
            sql_validator=sql_validator,
            sql_executor=executor_manager,
            result_validator=result_validator,
            schema_cache=schema_cache,
            pools={"test_db": mock_postgres_pool},
            resilience_config=mock_settings.resilience,
            validation_config=mock_settings.validation,
            circuit_breaker=mock_circuit_breaker,
            rate_limiter=mock_rate_limiter,
        )

        # Execute query
        request = QueryRequest(
            question="How many users are there?",
            database="test_db",
            return_type=ReturnType.RESULT,
        )

        response: QueryResponse = await orchestrator.execute_query(request)

        # Assertions
        assert response.success is True
        assert response.generated_sql is not None
        assert "SELECT COUNT(*)" in response.generated_sql.upper()
        assert response.data is not None
        assert response.data.row_count == 1
        assert response.error is None

    async def test_sql_only_query_flow(
        self,
        mock_openai,
        mock_postgres_pool,
        mock_settings,
        mock_circuit_breaker,
        mock_rate_limiter,
        mock_schema,
    ):
        """Test query flow that returns SQL only without execution."""
        # Setup
        mock_openai.set_response(
            "list all users",
            "SELECT * FROM users",
        )

        # Create components (similar to above)
        sql_generator = SQLGenerator(mock_settings.openai)
        sql_generator._client = mock_openai

        sql_validator = SQLValidator(config=mock_settings.security)

        executor = SQLExecutor(
            pool=mock_postgres_pool,
            security_config=mock_settings.security,
            db_config=mock_settings.database,
        )

        executor_manager = ExecutorManager(
            executors={"test_db": executor},
            default_database="test_db",
        )

        result_validator = ResultValidator(
            openai_config=mock_settings.openai,
            validation_config=mock_settings.validation,
        )
        result_validator._client = mock_openai

        schema_cache = SchemaCache(mock_settings.cache)
        schema_cache._cache["test_db"] = mock_schema

        orchestrator = QueryOrchestrator(
            sql_generator=sql_generator,
            sql_validator=sql_validator,
            sql_executor=executor_manager,
            result_validator=result_validator,
            schema_cache=schema_cache,
            pools={"test_db": mock_postgres_pool},
            resilience_config=mock_settings.resilience,
            validation_config=mock_settings.validation,
            circuit_breaker=mock_circuit_breaker,
            rate_limiter=mock_rate_limiter,
        )

        # Execute query (SQL only)
        request = QueryRequest(
            question="List all users",
            database="test_db",
            return_type=ReturnType.SQL,
        )

        response: QueryResponse = await orchestrator.execute_query(request)

        # Assertions
        assert response.success is True
        assert response.generated_sql is not None
        assert "SELECT" in response.generated_sql.upper()
        assert "FROM users" in response.generated_sql
        assert response.data is None  # No data when return_type=SQL

    async def test_query_with_security_violation(
        self,
        mock_openai,
        mock_postgres_pool,
        mock_settings,
        mock_circuit_breaker,
        mock_rate_limiter,
        mock_schema,
    ):
        """Test query flow with security violation."""
        # Setup: Mock returns a dangerous query
        mock_openai.set_response(
            "delete",
            "DELETE FROM users WHERE id = 1",
        )

        # Create components
        sql_generator = SQLGenerator(mock_settings.openai)
        sql_generator._client = mock_openai

        sql_validator = SQLValidator(config=mock_settings.security)

        executor = SQLExecutor(
            pool=mock_postgres_pool,
            security_config=mock_settings.security,
            db_config=mock_settings.database,
        )

        executor_manager = ExecutorManager(
            executors={"test_db": executor},
            default_database="test_db",
        )

        result_validator = ResultValidator(
            openai_config=mock_settings.openai,
            validation_config=mock_settings.validation,
        )

        schema_cache = SchemaCache(mock_settings.cache)
        schema_cache._cache["test_db"] = mock_schema

        orchestrator = QueryOrchestrator(
            sql_generator=sql_generator,
            sql_validator=sql_validator,
            sql_executor=executor_manager,
            result_validator=result_validator,
            schema_cache=schema_cache,
            pools={"test_db": mock_postgres_pool},
            resilience_config=mock_settings.resilience,
            validation_config=mock_settings.validation,
            circuit_breaker=mock_circuit_breaker,
            rate_limiter=mock_rate_limiter,
        )

        # Execute query
        request = QueryRequest(
            question="Delete user with id 1",
            database="test_db",
            return_type=ReturnType.RESULT,
        )

        response: QueryResponse = await orchestrator.execute_query(request)

        # Assertions
        assert response.success is False
        assert response.error is not None
        assert "security" in response.error.code.lower() or "violation" in response.error.message.lower()

    async def test_query_with_question_too_long(
        self,
        mock_openai,
        mock_postgres_pool,
        mock_settings,
        mock_circuit_breaker,
        mock_rate_limiter,
        mock_schema,
    ):
        """Test query with question exceeding max length."""
        # Create a very long question
        long_question = "A" * (mock_settings.validation.max_question_length + 1)

        # Create components
        sql_generator = SQLGenerator(mock_settings.openai)
        sql_generator._client = mock_openai

        sql_validator = SQLValidator(config=mock_settings.security)

        executor = SQLExecutor(
            pool=mock_postgres_pool,
            security_config=mock_settings.security,
            db_config=mock_settings.database,
        )

        executor_manager = ExecutorManager(
            executors={"test_db": executor},
            default_database="test_db",
        )

        result_validator = ResultValidator(
            openai_config=mock_settings.openai,
            validation_config=mock_settings.validation,
        )

        schema_cache = SchemaCache(mock_settings.cache)
        schema_cache._cache["test_db"] = mock_schema

        orchestrator = QueryOrchestrator(
            sql_generator=sql_generator,
            sql_validator=sql_validator,
            sql_executor=executor_manager,
            result_validator=result_validator,
            schema_cache=schema_cache,
            pools={"test_db": mock_postgres_pool},
            resilience_config=mock_settings.resilience,
            validation_config=mock_settings.validation,
            circuit_breaker=mock_circuit_breaker,
            rate_limiter=mock_rate_limiter,
        )

        # Execute query
        request = QueryRequest(
            question=long_question,
            database="test_db",
            return_type=ReturnType.RESULT,
        )

        response: QueryResponse = await orchestrator.execute_query(request)

        # Assertions
        assert response.success is False
        assert response.error is not None
        assert "too long" in response.error.message.lower() or "length" in response.error.message.lower()

    async def test_multi_database_support(
        self,
        mock_openai,
        mock_settings,
        mock_circuit_breaker,
        mock_rate_limiter,
        mock_schema,
    ):
        """Test query execution with multiple databases."""
        # Create two mock pools
        from tests.mocks.postgres_mock import MockPostgresPool

        pool1 = MockPostgresPool()
        pool1.set_query_result(
            "SELECT COUNT(*) FROM users",
            [{"count": 10}],
        )

        pool2 = MockPostgresPool()
        pool2.set_query_result(
            "SELECT COUNT(*) FROM users",
            [{"count": 20}],
        )

        # Setup
        mock_openai.set_response(
            "count users",
            "SELECT COUNT(*) FROM users",
        )

        sql_generator = SQLGenerator(mock_settings.openai)
        sql_generator._client = mock_openai

        sql_validator = SQLValidator(config=mock_settings.security)

        executor1 = SQLExecutor(
            pool=pool1,
            security_config=mock_settings.security,
            db_config=mock_settings.database,
        )

        executor2 = SQLExecutor(
            pool=pool2,
            security_config=mock_settings.security,
            db_config=mock_settings.database,
        )

        executor_manager = ExecutorManager(
            executors={"db1": executor1, "db2": executor2},
            default_database="db1",
        )

        result_validator = ResultValidator(
            openai_config=mock_settings.openai,
            validation_config=mock_settings.validation,
        )
        result_validator._client = mock_openai

        schema_cache = SchemaCache(mock_settings.cache)
        schema_cache._cache["db1"] = mock_schema
        schema_cache._cache["db2"] = mock_schema

        orchestrator = QueryOrchestrator(
            sql_generator=sql_generator,
            sql_validator=sql_validator,
            sql_executor=executor_manager,
            result_validator=result_validator,
            schema_cache=schema_cache,
            pools={"db1": pool1, "db2": pool2},
            resilience_config=mock_settings.resilience,
            validation_config=mock_settings.validation,
            circuit_breaker=mock_circuit_breaker,
            rate_limiter=mock_rate_limiter,
        )

        # Query database 1
        request1 = QueryRequest(
            question="Count users in db1",
            database="db1",
            return_type=ReturnType.RESULT,
        )
        response1 = await orchestrator.execute_query(request1)

        assert response1.success is True
        # Note: actual count verification depends on mock implementation

        # Query database 2
        request2 = QueryRequest(
            question="Count users in db2",
            database="db2",
            return_type=ReturnType.RESULT,
        )
        response2 = await orchestrator.execute_query(request2)

        assert response2.success is True
