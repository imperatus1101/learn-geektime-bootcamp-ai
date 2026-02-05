"""Query orchestrator for coordinating the complete query flow.

This module provides the QueryOrchestrator class that coordinates all components
of the query processing pipeline: SQL generation, validation, execution, and result
validation. It implements retry logic, error handling, and request tracking.
"""

import logging
import time
import uuid
from typing import Any

from asyncpg import Pool

from pg_mcp.cache.schema_cache import SchemaCache
from pg_mcp.observability.metrics import metrics
from pg_mcp.observability.tracing import get_request_id, request_context, set_request_id
from pg_mcp.config.settings import ResilienceConfig, ValidationConfig
from pg_mcp.models.errors import (
    DatabaseError,
    ErrorCode,
    LLMError,
    PgMcpError,
    SchemaLoadError,
    SecurityViolationError,
    SQLParseError,
    ValidationError,
)
from pg_mcp.models.query import (
    ErrorDetail,
    QueryRequest,
    QueryResponse,
    QueryResult,
    ReturnType,
    ValidationResult,
)
from pg_mcp.resilience.circuit_breaker import CircuitBreaker
from pg_mcp.resilience.rate_limiter import MultiRateLimiter
from pg_mcp.resilience.retry import RetryConfig, RetryExhaustedError, with_retry
from pg_mcp.services.result_validator import ResultValidator
from pg_mcp.services.sql_executor import ExecutorManager, SQLExecutor
from pg_mcp.services.sql_generator import SQLGenerator
from pg_mcp.services.sql_validator import SQLValidator

logger = logging.getLogger(__name__)


class QueryOrchestrator:
    """Orchestrates the complete query processing pipeline.

    This class coordinates SQL generation, validation, execution, and result
    validation. It implements retry logic with error feedback, circuit breaker
    pattern for fault tolerance, and comprehensive error handling.

    Example:
        >>> orchestrator = QueryOrchestrator(
        ...     sql_generator=generator,
        ...     sql_validator=validator,
        ...     sql_executor=executor,
        ...     result_validator=result_validator,
        ...     schema_cache=cache,
        ...     pools={"mydb": pool},
        ...     resilience_config=resilience_config,
        ...     validation_config=validation_config,
        ... )
        >>> response = await orchestrator.execute_query(QueryRequest(
        ...     question="How many users?",
        ...     database="mydb"
        ... ))
    """

    def __init__(
        self,
        sql_generator: SQLGenerator,
        sql_validator: SQLValidator,
        sql_executor: SQLExecutor | ExecutorManager,
        result_validator: ResultValidator,
        schema_cache: SchemaCache,
        pools: dict[str, Pool],
        resilience_config: ResilienceConfig,
        validation_config: ValidationConfig,
        circuit_breaker: CircuitBreaker | None = None,
        rate_limiter: MultiRateLimiter | None = None,
    ) -> None:
        """Initialize query orchestrator.

        Args:
            sql_generator: SQL generation service.
            sql_validator: SQL validation service.
            sql_executor: SQL execution service or ExecutorManager for multi-database support.
            result_validator: Result validator service.
            schema_cache: Schema cache instance.
            pools: Dictionary mapping database names to connection pools.
            resilience_config: Resilience configuration for retries and circuit breaker.
            validation_config: Validation configuration including thresholds.
            circuit_breaker: Optional shared circuit breaker instance (creates new if None).
            rate_limiter: Optional shared rate limiter instance.
        """
        self.sql_generator = sql_generator
        self.sql_validator = sql_validator
        self._sql_executor_or_manager = sql_executor  # Can be SQLExecutor or ExecutorManager
        self.result_validator = result_validator
        self.schema_cache = schema_cache
        self.pools = pools
        self.resilience_config = resilience_config
        self.validation_config = validation_config

        # Use provided circuit breaker or create new one
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=resilience_config.circuit_breaker_threshold,
            recovery_timeout=resilience_config.circuit_breaker_timeout,
        )

        # Store rate limiter (optional)
        self.rate_limiter = rate_limiter

        # Initialize retry configurations for different operations
        self._llm_retry_config = RetryConfig(
            max_attempts=resilience_config.max_retries,
            initial_delay=resilience_config.retry_delay,
            backoff_factor=resilience_config.backoff_factor,
            max_delay=60.0,
            retriable_exceptions=(LLMError,),
        )

        self._db_retry_config = RetryConfig(
            max_attempts=resilience_config.max_retries,
            initial_delay=resilience_config.retry_delay,
            backoff_factor=resilience_config.backoff_factor,
            max_delay=30.0,
            retriable_exceptions=(DatabaseError,),
        )

    def _get_executor(self, database: str | None = None) -> SQLExecutor:
        """Get executor for the specified database.

        Args:
            database: Database name, or None for default.

        Returns:
            SQLExecutor: The executor for the specified database.

        Raises:
            ValueError: If database is not found (when using ExecutorManager).
        """
        if isinstance(self._sql_executor_or_manager, ExecutorManager):
            return self._sql_executor_or_manager.get_executor(database)
        else:
            # Legacy single executor mode
            return self._sql_executor_or_manager

    async def execute_query(self, request: QueryRequest) -> QueryResponse:
        """Execute complete query flow from question to results.

        This method orchestrates the entire pipeline:
        1. Generate request_id for tracking
        2. Resolve and validate database name
        3. Load schema from cache
        4. Generate and validate SQL with retry logic
        5. Execute SQL (if return_type == RESULT)
        6. Validate results (optional)
        7. Return structured response

        Args:
            request: Query request containing question and parameters.

        Returns:
            QueryResponse: Complete response with SQL, results, or error information.

        Example:
            >>> response = await orchestrator.execute_query(
            ...     QueryRequest(question="Count all users", return_type="result")
            ... )
            >>> if response.success:
            ...     print(f"Found {response.data.row_count} rows")
        """
        # Generate request_id for full-chain tracing (or use existing from context)
        request_id = get_request_id() or str(uuid.uuid4())
        set_request_id(request_id)

        logger.info(
            "Starting query execution",
            extra={"request_id": request_id, "question": request.question[:100]},
        )

        # Start overall query timing
        query_start_time = time.time()
        database_name = "unknown"  # Track for metrics even if resolution fails

        try:
            # Step 0: Validate question length
            if len(request.question) > self.validation_config.max_question_length:
                logger.warning(
                    "Question too long",
                    extra={
                        "request_id": request_id,
                        "question_length": len(request.question),
                        "max_length": self.validation_config.max_question_length,
                    },
                )

                # Record validation failure metric
                query_duration = time.time() - query_start_time
                metrics.query_duration.observe(query_duration)
                metrics.increment_query_request("validation_failed", database_name)

                return QueryResponse(
                    success=False,
                    generated_sql=None,
                    validation=None,
                    data=None,
                    error=ErrorDetail(
                        code=ErrorCode.QUESTION_TOO_LONG.value,
                        message=f"Question exceeds maximum length of {self.validation_config.max_question_length} characters",
                        details={
                            "question_length": len(request.question),
                            "max_length": self.validation_config.max_question_length,
                        },
                    ),
                    confidence=0,
                    tokens_used=None,
                )

            # Step 1: Resolve database name
            database_name = self._resolve_database(request.database)
            logger.debug(
                "Resolved database",
                extra={"request_id": request_id, "database": database_name},
            )

            # Step 2: Get schema from cache
            schema = self.schema_cache.get(database_name)
            if schema is None:
                # Schema not in cache, load it
                pool = self.pools.get(database_name)
                if pool is None:
                    raise DatabaseError(
                        message=f"No connection pool available for database '{database_name}'",
                        details={"database": database_name},
                    )
                try:
                    schema = await self.schema_cache.load(database_name, pool)
                except Exception as e:
                    raise SchemaLoadError(
                        message=f"Failed to load schema for database '{database_name}': {e!s}",
                        details={"database": database_name, "error": str(e)},
                    ) from e

            logger.debug(
                "Schema loaded",
                extra={
                    "request_id": request_id,
                    "database": database_name,
                    "tables": len(schema.tables),
                },
            )

            # Step 3: Generate and validate SQL with retry logic
            sql_gen_start = time.time()
            generated_sql, validation_result, tokens_used = await self._generate_sql_with_retry(
                question=request.question,
                schema=schema,
                request_id=request_id,
            )
            sql_gen_duration = time.time() - sql_gen_start

            # Record SQL generation metrics
            metrics.increment_llm_call("generate_sql")
            metrics.observe_llm_latency("generate_sql", sql_gen_duration)
            if tokens_used:
                metrics.increment_llm_tokens("generate_sql", tokens_used)

            # Step 4: If return_type is SQL, return early
            if request.return_type == ReturnType.SQL:
                logger.info(
                    "Returning SQL only",
                    extra={"request_id": request_id, "sql_length": len(generated_sql)},
                )

                # Record successful query (SQL only)
                query_duration = time.time() - query_start_time
                metrics.query_duration.observe(query_duration)
                metrics.increment_query_request("success", database_name)

                return QueryResponse(
                    success=True,
                    generated_sql=generated_sql,
                    validation=validation_result,
                    data=None,
                    error=None,
                    confidence=100,
                    tokens_used=tokens_used,
                )

            # Step 5: Execute SQL with resilience protection
            logger.debug("Executing SQL", extra={"request_id": request_id})
            start_time = self._get_current_time_ms()

            # Get executor for the resolved database
            executor = self._get_executor(database_name)

            # Execute with retry and resilience protection
            results, total_count = await self._execute_with_resilience(
                executor, generated_sql, request_id
            )

            execution_time_ms = self._get_current_time_ms() - start_time
            logger.info(
                "SQL executed successfully",
                extra={
                    "request_id": request_id,
                    "row_count": total_count,
                    "execution_time_ms": execution_time_ms,
                },
            )

            # Record database execution metrics
            metrics.observe_db_query_duration(execution_time_ms / 1000.0)

            # Step 6: Validate results (non-blocking, failures don't fail the request)
            result_confidence = await self._validate_results_safely(
                question=request.question,
                sql=generated_sql,
                results=results,
                row_count=total_count,
                request_id=request_id,
            )

            # Step 6.5: Check confidence threshold
            if result_confidence < self.validation_config.min_confidence_score:
                logger.warning(
                    "Result confidence below threshold",
                    extra={
                        "request_id": request_id,
                        "confidence": result_confidence,
                        "threshold": self.validation_config.min_confidence_score,
                    },
                )

                # Record low confidence metric
                query_duration = time.time() - query_start_time
                metrics.query_duration.observe(query_duration)
                metrics.increment_query_request("low_confidence", database_name)

                return QueryResponse(
                    success=False,
                    generated_sql=generated_sql,
                    validation=validation_result,
                    data=None,
                    error=ErrorDetail(
                        code="LOW_CONFIDENCE",
                        message=(
                            f"Result confidence {result_confidence}% is below the "
                            f"required threshold of {self.validation_config.min_confidence_score}%"
                        ),
                        details={
                            "confidence": result_confidence,
                            "threshold": self.validation_config.min_confidence_score,
                        },
                    ),
                    confidence=result_confidence,
                    tokens_used=tokens_used,
                )

            # Step 7: Build successful response
            query_result = QueryResult(
                columns=list(results[0].keys()) if results else [],
                rows=results,
                row_count=len(results),  # Limited row count (after max_rows applied)
                execution_time_ms=execution_time_ms,
            )

            # Record overall query success metrics
            query_duration = time.time() - query_start_time
            metrics.query_duration.observe(query_duration)
            metrics.increment_query_request("success", database_name)

            return QueryResponse(
                success=True,
                generated_sql=generated_sql,
                validation=validation_result,
                data=query_result,
                error=None,
                confidence=result_confidence,
                tokens_used=tokens_used,
            )

        except PgMcpError as e:
            # Handle known application errors
            logger.warning(
                "Query execution failed with known error",
                extra={
                    "request_id": request_id,
                    "error_code": e.code,
                    "error_message": str(e),
                },
            )

            # Record error metrics
            query_duration = time.time() - query_start_time
            metrics.query_duration.observe(query_duration)

            # Categorize error for metrics
            if isinstance(e, SecurityViolationError):
                metrics.increment_query_request("security_violation", database_name)
                metrics.increment_sql_rejected(str(e.code))
            elif isinstance(e, (SQLParseError, ValidationError)):
                metrics.increment_query_request("validation_failed", database_name)
            else:
                metrics.increment_query_request("error", database_name)

            return QueryResponse(
                success=False,
                generated_sql=None,
                validation=None,
                data=None,
                error=ErrorDetail(
                    code=e.code.value,
                    message=e.message,
                    details=e.details,
                ),
                confidence=0,
                tokens_used=None,
            )
        except Exception as e:
            # Handle unexpected errors
            logger.exception(
                "Query execution failed with unexpected error",
                extra={"request_id": request_id},
            )

            # Record error metrics
            query_duration = time.time() - query_start_time
            metrics.query_duration.observe(query_duration)
            metrics.increment_query_request("error", database_name)

            return QueryResponse(
                success=False,
                generated_sql=None,
                validation=None,
                data=None,
                error=ErrorDetail(
                    code=ErrorCode.INTERNAL_ERROR.value,
                    message=f"Internal server error: {e!s}",
                    details={"error_type": type(e).__name__},
                ),
                confidence=0,
                tokens_used=None,
            )

    def _resolve_database(self, database: str | None) -> str:
        """Resolve database name from request or auto-select.

        If database is specified, validate it exists.
        If not specified and only one database available, auto-select it.

        Args:
            database: Database name from request (optional).

        Returns:
            str: Resolved database name.

        Raises:
            DatabaseError: If database is invalid or cannot be auto-selected.

        Example:
            >>> name = orchestrator._resolve_database("mydb")  # Validates "mydb" exists
            >>> name = orchestrator._resolve_database(None)  # Auto-selects if only one DB
        """
        if database is not None:
            # Validate specified database exists
            if database not in self.pools:
                raise DatabaseError(
                    message=f"Database '{database}' not found",
                    details={
                        "requested_database": database,
                        "available_databases": list(self.pools.keys()),
                    },
                )
            return database

        # Auto-select if only one database available
        available_dbs = list(self.pools.keys())
        if len(available_dbs) == 0:
            raise DatabaseError(
                message="No databases configured",
                details={},
            )
        if len(available_dbs) == 1:
            return available_dbs[0]

        # Multiple databases, must specify
        raise DatabaseError(
            message="Multiple databases available, please specify which to query",
            details={"available_databases": available_dbs},
        )

    async def _generate_sql_with_retry(
        self,
        question: str,
        schema: Any,
        request_id: str,
    ) -> tuple[str, ValidationResult, int | None]:
        """Generate and validate SQL with retry logic on validation failures.

        This method implements a retry loop that:
        1. Checks circuit breaker state
        2. Generates SQL using LLM
        3. Validates the generated SQL
        4. On validation failure, retries with error feedback
        5. Records success/failure to circuit breaker

        Args:
            question: User's natural language question.
            schema: Database schema for context.
            request_id: Request ID for tracking.

        Returns:
            tuple: (generated_sql, validation_result, tokens_used)

        Raises:
            LLMError: If circuit breaker is open or generation fails.
            SecurityViolationError: If SQL fails validation after all retries.
            SQLParseError: If SQL cannot be parsed.

        Example:
            >>> sql, validation, tokens = await orchestrator._generate_sql_with_retry(
            ...     question="Count users",
            ...     schema=db_schema,
            ...     request_id="123",
            ... )
        """
        # Check circuit breaker
        if not self.circuit_breaker.allow_request():
            raise LLMError(
                message="SQL generation service is temporarily unavailable (circuit breaker open)",
                details={
                    "circuit_state": self.circuit_breaker.state,
                    "failure_count": self.circuit_breaker.failure_count,
                },
            )

        previous_sql: str | None = None
        error_feedback: str | None = None
        max_retries = self.resilience_config.max_retries
        tokens_used: int | None = None

        for attempt in range(max_retries + 1):
            try:
                logger.debug(
                    "Generating SQL",
                    extra={
                        "request_id": request_id,
                        "attempt": attempt + 1,
                        "max_retries": max_retries + 1,
                    },
                )

                # Generate SQL
                generated_sql = await self.sql_generator.generate(
                    question=question,
                    schema=schema,
                    previous_attempt=previous_sql,
                    error_feedback=error_feedback,
                )

                # Note: tokens_used would come from OpenAI response metadata if available
                # For now, we don't extract it, but it can be added later

                logger.debug(
                    "SQL generated",
                    extra={
                        "request_id": request_id,
                        "sql_length": len(generated_sql),
                    },
                )

                # Validate SQL
                try:
                    self.sql_validator.validate_or_raise(generated_sql)
                except (SecurityViolationError, SQLParseError) as validation_error:
                    if attempt < max_retries:
                        # Record as failure and retry with feedback
                        logger.warning(
                            "SQL validation failed, retrying with feedback",
                            extra={
                                "request_id": request_id,
                                "attempt": attempt + 1,
                                "error": str(validation_error),
                            },
                        )
                        previous_sql = generated_sql
                        error_feedback = str(validation_error)
                        continue
                    else:
                        # Out of retries, record failure and raise
                        self.circuit_breaker.record_failure()
                        logger.error(
                            "SQL validation failed after all retries",
                            extra={
                                "request_id": request_id,
                                "attempts": attempt + 1,
                                "error": str(validation_error),
                            },
                        )
                        raise

                # Validation successful
                self.circuit_breaker.record_success()
                logger.info(
                    "SQL generated and validated successfully",
                    extra={
                        "request_id": request_id,
                        "attempts": attempt + 1,
                    },
                )

                # Build validation result
                validation_result = ValidationResult(
                    is_valid=True,
                    is_select=True,
                    allows_data_modification=False,
                    uses_blocked_functions=[],
                    error_message=None,
                )

                return generated_sql, validation_result, tokens_used

            except (LLMError, SecurityViolationError, SQLParseError):
                # Re-raise known errors
                raise
            except Exception as e:
                # Unexpected error during generation
                self.circuit_breaker.record_failure()
                logger.exception(
                    "Unexpected error during SQL generation",
                    extra={"request_id": request_id},
                )
                raise LLMError(
                    message=f"SQL generation failed unexpectedly: {e!s}",
                    details={"error_type": type(e).__name__},
                ) from e

        # Should not reach here, but just in case
        self.circuit_breaker.record_failure()
        raise LLMError(
            message="SQL generation failed after all retry attempts",
            details={"max_retries": max_retries},
        )

    async def _validate_results_safely(
        self,
        question: str,
        sql: str,
        results: list[dict[str, Any]],
        row_count: int,
        request_id: str,
    ) -> int:
        """Validate query results with error handling (non-blocking).

        This method attempts to validate results using LLM, but failures
        don't cause the overall query to fail. Returns a confidence score.

        Args:
            question: User's original question.
            sql: Generated SQL query.
            results: Query results.
            row_count: Total row count.
            request_id: Request ID for tracking.

        Returns:
            int: Confidence score (0-100). Returns 100 if validation disabled/fails.

        Example:
            >>> confidence = await orchestrator._validate_results_safely(
            ...     question="Count users",
            ...     sql="SELECT COUNT(*) FROM users",
            ...     results=[{"count": 42}],
            ...     row_count=1,
            ...     request_id="123",
            ... )
        """
        if not self.validation_config.enabled:
            return 100

        try:
            logger.debug(
                "Validating results",
                extra={"request_id": request_id},
            )

            validation_result = await self.result_validator.validate(
                question=question,
                sql=sql,
                results=results,
                row_count=row_count,
            )

            logger.info(
                "Result validation completed",
                extra={
                    "request_id": request_id,
                    "confidence": validation_result.confidence,
                    "is_acceptable": validation_result.is_acceptable,
                },
            )

            return validation_result.confidence

        except Exception as e:
            # Log but don't fail the query
            logger.warning(
                "Result validation failed, continuing with default confidence",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                },
            )
            return 100  # Default to high confidence if validation fails

    async def _execute_with_resilience(
        self,
        executor: SQLExecutor,
        sql: str,
        request_id: str,
    ) -> tuple[list[dict[str, Any]], int]:
        """Execute SQL with full resilience protection (retry, circuit breaker, rate limiting).

        This method applies multiple layers of protection:
        1. Rate limiting (if configured)
        2. Circuit breaker protection
        3. Automatic retry with exponential backoff for transient failures

        Args:
            executor: SQL executor to use.
            sql: SQL query to execute.
            request_id: Request ID for tracking.

        Returns:
            tuple: (results, total_count) from executor.

        Raises:
            RetryExhaustedError: If all retry attempts fail.
            DatabaseError: If execution fails after retries.
        """

        @with_retry(self._db_retry_config)
        async def _execute_with_protection() -> tuple[list[dict[str, Any]], int]:
            # Apply rate limiting if configured
            if self.rate_limiter is not None:
                await self.rate_limiter.acquire("database")
                logger.debug(
                    "Rate limit acquired for database operation",
                    extra={"request_id": request_id},
                )

            # Check circuit breaker before execution
            if not self.circuit_breaker.allow_request():
                raise DatabaseError(
                    message="Database service temporarily unavailable (circuit breaker open)",
                    details={
                        "circuit_state": self.circuit_breaker.state,
                        "failure_count": self.circuit_breaker.failure_count,
                    },
                )

            try:
                # Execute the query
                results, total_count = await executor.execute(sql)

                # Record success in circuit breaker
                self.circuit_breaker.record_success()

                return results, total_count

            except Exception as e:
                # Record failure in circuit breaker
                self.circuit_breaker.record_failure()

                # Convert to DatabaseError for retry logic
                if isinstance(e, DatabaseError):
                    raise
                else:
                    raise DatabaseError(
                        message=f"Database execution failed: {e!s}",
                        details={"error_type": type(e).__name__},
                    ) from e

        try:
            return await _execute_with_protection()
        except RetryExhaustedError as e:
            logger.error(
                "Database execution failed after all retries",
                extra={
                    "request_id": request_id,
                    "attempts": e.attempts,
                    "last_error": str(e.last_error),
                },
            )
            # Re-raise as DatabaseError for consistent error handling
            raise DatabaseError(
                message=f"Database execution failed after {e.attempts} attempts",
                details={"last_error": str(e.last_error)},
            ) from e

    @staticmethod
    def _get_current_time_ms() -> float:
        """Get current time in milliseconds.

        Returns:
            float: Current time in milliseconds since epoch.
        """
        import time

        return time.time() * 1000
