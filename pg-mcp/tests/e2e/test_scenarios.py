"""End-to-end scenario tests with mocks.

This module tests complete user scenarios using mock dependencies,
ensuring all tests can run offline and deterministically.
"""

import pytest

from pg_mcp.cache.schema_cache import SchemaCache
from pg_mcp.models.query import QueryRequest, ReturnType
from pg_mcp.services.orchestrator import QueryOrchestrator
from pg_mcp.services.result_validator import ResultValidator
from pg_mcp.services.sql_executor import ExecutorManager, SQLExecutor
from pg_mcp.services.sql_generator import SQLGenerator
from pg_mcp.services.sql_validator import SQLValidator


@pytest.mark.asyncio
class TestUserScenarios:
    """Test realistic user scenarios end-to-end."""

    async def test_basic_count_query(
        self,
        mock_openai,
        mock_postgres_pool,
        mock_settings,
        mock_circuit_breaker,
        mock_rate_limiter,
        mock_schema,
    ):
        """Test: User asks 'How many users are there?'"""
        mock_openai.set_response("how many users", "SELECT COUNT(*) FROM users")

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

        request = QueryRequest(
            question="How many users are there?",
            database="test_db",
            return_type=ReturnType.RESULT,
        )

        response = await orchestrator.execute_query(request)

        assert response.success is True
        assert response.data is not None
        assert response.data.row_count >= 1

    async def test_aggregation_query(
        self,
        mock_openai,
        mock_postgres_pool,
        mock_settings,
        mock_circuit_breaker,
        mock_rate_limiter,
        mock_schema,
    ):
        """Test: User asks for total order amount."""
        mock_openai.set_response("total order", "SELECT SUM(amount) FROM orders")

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

        request = QueryRequest(
            question="What is the total order amount?",
            database="test_db",
            return_type=ReturnType.RESULT,
        )

        response = await orchestrator.execute_query(request)

        assert response.success is True
        assert response.generated_sql is not None
        assert "SUM" in response.generated_sql.upper()

    async def test_security_blocked_table_access(
        self,
        mock_openai,
        mock_postgres_pool,
        mock_circuit_breaker,
        mock_rate_limiter,
        mock_schema,
    ):
        """Test: Security blocks access to sensitive tables."""
        from pg_mcp.config.settings import SecurityConfig, Settings

        # Create settings with blocked tables
        settings = Settings(
            database=mock_postgres_pool._min_size.__self__.__class__.__bases__[0].__dict__.get(
                "database", type("DatabaseConfig", (), {
                    "host": "localhost",
                    "port": 5432,
                    "name": "test_db",
                    "user": "test",
                    "password": "test",
                })()
            ),
            openai=type("OpenAIConfig", (), {
                "api_key": "sk-test",
                "model": "gpt-4o-mini",
                "max_tokens": 1000,
                "temperature": 0.0,
                "timeout": 10.0,
            })(),
            security=SecurityConfig(
                blocked_tables=["users_sensitive", "audit_*"],
                blocked_functions=[],
                max_rows=1000,
                max_execution_time=10.0,
            ),
            validation=type("ValidationConfig", (), {
                "max_question_length": 5000,
                "min_confidence_score": 70,
                "enabled": False,
            })(),
            cache=type("CacheConfig", (), {
                "schema_ttl": 3600,
                "enabled": True,
            })(),
            resilience=type("ResilienceConfig", (), {
                "max_retries": 2,
                "retry_delay": 0.1,
                "backoff_factor": 2.0,
                "circuit_breaker_threshold": 3,
                "circuit_breaker_timeout": 5.0,
            })(),
            observability=type("ObservabilityConfig", (), {
                "metrics_enabled": False,
            })(),
        )

        mock_openai.set_response(
            "users_sensitive",
            "SELECT * FROM users_sensitive",
        )

        sql_generator = SQLGenerator(settings.openai)
        sql_generator._client = mock_openai

        sql_validator = SQLValidator(config=settings.security)

        executor = SQLExecutor(
            pool=mock_postgres_pool,
            security_config=settings.security,
            db_config=settings.database,
        )

        executor_manager = ExecutorManager(
            executors={"test_db": executor},
            default_database="test_db",
        )

        result_validator = ResultValidator(
            openai_config=settings.openai,
            validation_config=settings.validation,
        )

        schema_cache = SchemaCache(settings.cache)
        schema_cache._cache["test_db"] = mock_schema

        orchestrator = QueryOrchestrator(
            sql_generator=sql_generator,
            sql_validator=sql_validator,
            sql_executor=executor_manager,
            result_validator=result_validator,
            schema_cache=schema_cache,
            pools={"test_db": mock_postgres_pool},
            resilience_config=settings.resilience,
            validation_config=settings.validation,
            circuit_breaker=mock_circuit_breaker,
            rate_limiter=mock_rate_limiter,
        )

        request = QueryRequest(
            question="Show me data from users_sensitive table",
            database="test_db",
            return_type=ReturnType.RESULT,
        )

        response = await orchestrator.execute_query(request)

        assert response.success is False
        assert response.error is not None

    async def test_empty_result_handling(
        self,
        mock_openai,
        mock_settings,
        mock_circuit_breaker,
        mock_rate_limiter,
        mock_schema,
    ):
        """Test: Query returns no results."""
        from tests.mocks.postgres_mock import MockPostgresPool

        pool = MockPostgresPool()
        pool.set_query_result(
            "SELECT * FROM users WHERE id = 999",
            [],  # Empty result
        )

        mock_openai.set_response(
            "user 999",
            "SELECT * FROM users WHERE id = 999",
        )

        sql_generator = SQLGenerator(mock_settings.openai)
        sql_generator._client = mock_openai

        sql_validator = SQLValidator(config=mock_settings.security)

        executor = SQLExecutor(
            pool=pool,
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
            pools={"test_db": pool},
            resilience_config=mock_settings.resilience,
            validation_config=mock_settings.validation,
            circuit_breaker=mock_circuit_breaker,
            rate_limiter=mock_rate_limiter,
        )

        request = QueryRequest(
            question="Find user with id 999",
            database="test_db",
            return_type=ReturnType.RESULT,
        )

        response = await orchestrator.execute_query(request)

        assert response.success is True
        assert response.data is not None
        assert response.data.row_count == 0

    async def test_complex_join_query(
        self,
        mock_openai,
        mock_postgres_pool,
        mock_settings,
        mock_circuit_breaker,
        mock_rate_limiter,
        mock_schema,
    ):
        """Test: Complex query with JOIN."""
        mock_openai.set_response(
            "users with orders",
            "SELECT u.name, o.amount FROM users u JOIN orders o ON u.id = o.user_id",
        )

        # Add JOIN result to mock pool
        mock_postgres_pool.set_query_result(
            "join orders",
            [
                {"name": "Alice", "amount": 100.50},
                {"name": "Bob", "amount": 250.00},
            ],
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

        request = QueryRequest(
            question="Show me users with their orders",
            database="test_db",
            return_type=ReturnType.RESULT,
        )

        response = await orchestrator.execute_query(request)

        assert response.success is True
        assert "JOIN" in response.generated_sql.upper()
