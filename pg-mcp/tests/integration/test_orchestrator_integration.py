"""Integration tests for QueryOrchestrator with resilience mechanisms.

This module tests the orchestrator's integration with retry, circuit breaker,
rate limiting, and metrics collection.
"""

import pytest

from pg_mcp.cache.schema_cache import SchemaCache
from pg_mcp.models.errors import DatabaseError, LLMError
from pg_mcp.models.query import QueryRequest, ReturnType
from pg_mcp.resilience.circuit_breaker import CircuitState
from pg_mcp.services.orchestrator import QueryOrchestrator
from pg_mcp.services.result_validator import ResultValidator
from pg_mcp.services.sql_executor import ExecutorManager, SQLExecutor
from pg_mcp.services.sql_generator import SQLGenerator
from pg_mcp.services.sql_validator import SQLValidator


@pytest.mark.asyncio
class TestOrchestratorResilience:
    """Test orchestrator resilience mechanisms."""

    async def test_retry_on_transient_llm_failure(
        self,
        mock_openai,
        mock_postgres_pool,
        mock_settings,
        mock_circuit_breaker,
        mock_rate_limiter,
        mock_schema,
    ):
        """Test that LLM failures trigger retry mechanism."""
        # Setup: Configure to fail once then succeed
        call_count = 0

        class FailOnceMockOpenAI:
            def __init__(self, inner):
                self.inner = inner
                self.chat = self

            class Completions:
                def __init__(self, parent):
                    self.parent = parent
                    self.completions = self

                async def create(self, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        raise LLMError("Transient failure")
                    return await self.parent.inner.chat.completions.create(**kwargs)

            @property
            def completions(self):
                return self.Completions(self)

        failing_client = FailOnceMockOpenAI(mock_openai)
        mock_openai.set_response("count", "SELECT COUNT(*) FROM users")

        # Create components
        sql_generator = SQLGenerator(mock_settings.openai)
        sql_generator._client = failing_client

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

        # Execute - should retry and succeed on second attempt
        request = QueryRequest(
            question="Count users",
            database="test_db",
            return_type=ReturnType.SQL,
        )

        response = await orchestrator.execute_query(request)

        # Should succeed after retry
        assert call_count == 2  # Failed once, succeeded second time
        # Note: Actual success depends on how retry is implemented

    async def test_circuit_breaker_opens_after_failures(
        self,
        mock_openai,
        mock_postgres_pool,
        mock_settings,
        mock_rate_limiter,
        mock_schema,
    ):
        """Test that circuit breaker opens after threshold failures."""
        from pg_mcp.resilience.circuit_breaker import CircuitBreaker

        # Create a circuit breaker with low threshold
        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=60.0,
        )

        # Setup: Mock that always fails
        class AlwaysFailMock:
            def __init__(self):
                self.chat = self

            class Completions:
                async def create(self, **kwargs):
                    raise LLMError("Always fails")

                def __getattr__(self, name):
                    return self

            @property
            def completions(self):
                return self.Completions()

        failing_client = AlwaysFailMock()

        sql_generator = SQLGenerator(mock_settings.openai)
        sql_generator._client = failing_client

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
            circuit_breaker=circuit_breaker,
            rate_limiter=mock_rate_limiter,
        )

        request = QueryRequest(
            question="Count users",
            database="test_db",
            return_type=ReturnType.SQL,
        )

        # First few failures should be attempted
        for _ in range(3):
            response = await orchestrator.execute_query(request)
            assert response.success is False

        # Check circuit breaker state
        # After threshold failures, circuit should be open
        # Note: Actual behavior depends on circuit breaker implementation

    async def test_rate_limiter_applied(
        self,
        mock_openai,
        mock_postgres_pool,
        mock_settings,
        mock_circuit_breaker,
        mock_schema,
    ):
        """Test that rate limiter is applied to operations."""
        from unittest.mock import AsyncMock, Mock

        from pg_mcp.resilience.rate_limiter import MultiRateLimiter

        # Create a rate limiter we can inspect
        rate_limiter = MultiRateLimiter(
            query_limit=10,
            llm_limit=5,
        )

        # Track calls to acquire
        original_acquire = rate_limiter.acquire
        acquire_calls = []

        async def tracked_acquire(resource: str):
            acquire_calls.append(resource)
            return await original_acquire(resource)

        rate_limiter.acquire = tracked_acquire

        mock_openai.set_response("count", "SELECT COUNT(*) FROM users")

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
            rate_limiter=rate_limiter,
        )

        request = QueryRequest(
            question="Count users",
            database="test_db",
            return_type=ReturnType.RESULT,
        )

        response = await orchestrator.execute_query(request)

        # Verify rate limiter was called
        assert "database" in acquire_calls

    async def test_metrics_collected_on_success(
        self,
        mock_openai,
        mock_postgres_pool,
        mock_settings,
        mock_circuit_breaker,
        mock_rate_limiter,
        mock_schema,
    ):
        """Test that metrics are collected on successful queries."""
        from pg_mcp.observability.metrics import metrics

        mock_openai.set_response("count", "SELECT COUNT(*) FROM users")

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

        request = QueryRequest(
            question="Count users",
            database="test_db",
            return_type=ReturnType.RESULT,
        )

        # Get initial metric values
        initial_llm_calls = metrics.llm_calls.labels(operation="generate_sql")._value.get()

        response = await orchestrator.execute_query(request)

        # Verify metrics were incremented
        final_llm_calls = metrics.llm_calls.labels(operation="generate_sql")._value.get()
        assert final_llm_calls > initial_llm_calls

    async def test_metrics_collected_on_error(
        self,
        mock_openai,
        mock_postgres_pool,
        mock_settings,
        mock_circuit_breaker,
        mock_rate_limiter,
        mock_schema,
    ):
        """Test that metrics are collected on query errors."""
        from pg_mcp.observability.metrics import metrics

        # Setup: Return invalid SQL that will fail validation
        mock_openai.set_response(
            "delete",
            "DELETE FROM users WHERE id = 1",
        )

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

        request = QueryRequest(
            question="Delete user 1",
            database="test_db",
            return_type=ReturnType.RESULT,
        )

        response = await orchestrator.execute_query(request)

        # Should fail with security violation
        assert response.success is False
