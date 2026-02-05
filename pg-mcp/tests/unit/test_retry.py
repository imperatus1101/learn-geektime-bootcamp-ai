"""Unit tests for retry mechanism with exponential backoff."""

import asyncio
from typing import Any

import pytest

from pg_mcp.resilience.retry import RetryConfig, RetryExhaustedError, retry_async, with_retry


class TestRetryConfig:
    """Test suite for RetryConfig class."""

    def test_valid_config_creation(self) -> None:
        """Test creating valid RetryConfig."""
        config = RetryConfig(
            max_attempts=5,
            initial_delay=2.0,
            backoff_factor=3.0,
            max_delay=100.0,
        )

        assert config.max_attempts == 5
        assert config.initial_delay == 2.0
        assert config.backoff_factor == 3.0
        assert config.max_delay == 100.0

    def test_invalid_max_attempts(self) -> None:
        """Test that max_attempts must be >= 1."""
        with pytest.raises(ValueError, match="max_attempts must be >= 1"):
            RetryConfig(max_attempts=0)

    def test_invalid_initial_delay(self) -> None:
        """Test that initial_delay must be >= 0."""
        with pytest.raises(ValueError, match="initial_delay must be >= 0"):
            RetryConfig(initial_delay=-1.0)

    def test_invalid_backoff_factor(self) -> None:
        """Test that backoff_factor must be >= 1.0."""
        with pytest.raises(ValueError, match="backoff_factor must be >= 1.0"):
            RetryConfig(backoff_factor=0.5)

    def test_invalid_max_delay(self) -> None:
        """Test that max_delay must be >= initial_delay."""
        with pytest.raises(ValueError, match="max_delay must be >= initial_delay"):
            RetryConfig(initial_delay=10.0, max_delay=5.0)

    def test_calculate_delay_exponential_backoff(self) -> None:
        """Test exponential backoff delay calculation."""
        config = RetryConfig(
            initial_delay=1.0,
            backoff_factor=2.0,
            max_delay=10.0,
        )

        # Test exponential growth: delay = 1.0 * (2.0 ** attempt)
        assert config.calculate_delay(0) == 1.0  # 1.0 * 2^0 = 1.0
        assert config.calculate_delay(1) == 2.0  # 1.0 * 2^1 = 2.0
        assert config.calculate_delay(2) == 4.0  # 1.0 * 2^2 = 4.0
        assert config.calculate_delay(3) == 8.0  # 1.0 * 2^3 = 8.0
        assert config.calculate_delay(4) == 10.0  # 1.0 * 2^4 = 16.0, capped at 10.0

    def test_calculate_delay_respects_max_delay(self) -> None:
        """Test that calculated delay never exceeds max_delay."""
        config = RetryConfig(
            initial_delay=5.0,
            backoff_factor=3.0,
            max_delay=20.0,
        )

        # 5.0 * 3^5 = 1215.0, should be capped at 20.0
        assert config.calculate_delay(5) == 20.0
        assert config.calculate_delay(10) == 20.0

    def test_calculate_delay_with_factor_one(self) -> None:
        """Test constant delay when backoff_factor is 1.0."""
        config = RetryConfig(
            initial_delay=5.0,
            backoff_factor=1.0,
            max_delay=10.0,
        )

        # Should stay constant at initial_delay
        assert config.calculate_delay(0) == 5.0
        assert config.calculate_delay(1) == 5.0
        assert config.calculate_delay(10) == 5.0


class TestRetryDecorator:
    """Test suite for @with_retry decorator."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt(self) -> None:
        """Test that function returning successfully on first try doesn't retry."""
        call_count = 0

        @with_retry(RetryConfig(max_attempts=3))
        async def successful_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_func()

        assert result == "success"
        assert call_count == 1  # Only called once

    @pytest.mark.asyncio
    async def test_succeeds_after_retries(self) -> None:
        """Test that function succeeds after transient failures."""
        call_count = 0

        @with_retry(
            RetryConfig(
                max_attempts=3,
                initial_delay=0.01,  # Fast for testing
                retriable_exceptions=(ValueError,),
            )
        )
        async def eventually_successful_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Transient error")
            return "success"

        result = await eventually_successful_func()

        assert result == "success"
        assert call_count == 3  # Failed twice, succeeded third time

    @pytest.mark.asyncio
    async def test_exhausts_retries(self) -> None:
        """Test that RetryExhaustedError is raised after all attempts fail."""
        call_count = 0

        @with_retry(
            RetryConfig(
                max_attempts=3,
                initial_delay=0.01,
                retriable_exceptions=(ValueError,),
            )
        )
        async def always_failing_func() -> None:
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent error")

        with pytest.raises(RetryExhaustedError) as exc_info:
            await always_failing_func()

        assert exc_info.value.attempts == 3
        assert call_count == 3
        assert isinstance(exc_info.value.last_error, ValueError)
        assert "Persistent error" in str(exc_info.value.last_error)

    @pytest.mark.asyncio
    async def test_only_retries_specified_exceptions(self) -> None:
        """Test that only retriable exceptions trigger retry."""

        @with_retry(
            RetryConfig(
                max_attempts=3,
                initial_delay=0.01,
                retriable_exceptions=(ValueError,),  # Only ValueError is retriable
            )
        )
        async def func_raising_non_retriable() -> None:
            raise TypeError("Non-retriable error")

        # TypeError should propagate immediately without retry
        with pytest.raises(TypeError, match="Non-retriable error"):
            await func_raising_non_retriable()

    @pytest.mark.asyncio
    async def test_retry_with_arguments(self) -> None:
        """Test that decorated function correctly passes arguments."""
        call_count = 0

        @with_retry(
            RetryConfig(
                max_attempts=2,
                initial_delay=0.01,
            )
        )
        async def func_with_args(x: int, y: str, *, z: bool = False) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First attempt fails")
            return {"x": x, "y": y, "z": z}

        result = await func_with_args(42, "hello", z=True)

        assert result == {"x": 42, "y": "hello", "z": True}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_delay_between_retries(self) -> None:
        """Test that actual delay occurs between retries."""
        call_times: list[float] = []

        @with_retry(
            RetryConfig(
                max_attempts=3,
                initial_delay=0.05,  # 50ms initial delay
                backoff_factor=2.0,
            )
        )
        async def func_tracking_time() -> None:
            import time

            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("Retry me")

        await func_tracking_time()

        assert len(call_times) == 3

        # Check delays between calls
        # First retry: ~0.05s delay
        delay_1 = call_times[1] - call_times[0]
        assert 0.04 < delay_1 < 0.15  # Allow some tolerance

        # Second retry: ~0.10s delay (0.05 * 2^1)
        delay_2 = call_times[2] - call_times[1]
        assert 0.08 < delay_2 < 0.20

    @pytest.mark.asyncio
    async def test_multiple_exception_types_retriable(self) -> None:
        """Test retrying multiple exception types."""
        call_count = 0

        @with_retry(
            RetryConfig(
                max_attempts=4,
                initial_delay=0.01,
                retriable_exceptions=(ValueError, TypeError, KeyError),
            )
        )
        async def func_raising_different_exceptions() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First error")
            elif call_count == 2:
                raise TypeError("Second error")
            elif call_count == 3:
                raise KeyError("Third error")
            return "success"

        result = await func_raising_different_exceptions()

        assert result == "success"
        assert call_count == 4


class TestRetryAsync:
    """Test suite for retry_async functional helper."""

    @pytest.mark.asyncio
    async def test_retry_async_success(self) -> None:
        """Test successful retry_async call."""
        call_count = 0

        async def func(x: int) -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry")
            return x * 2

        result = await retry_async(
            func,
            RetryConfig(max_attempts=3, initial_delay=0.01),
            5,
        )

        assert result == 10
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_async_with_kwargs(self) -> None:
        """Test retry_async with keyword arguments."""

        async def func(a: int, b: int, *, multiply: bool = False) -> int:
            if multiply:
                return a * b
            return a + b

        result = await retry_async(
            func,
            RetryConfig(max_attempts=1, initial_delay=0.01),
            10,
            20,
            multiply=True,
        )

        assert result == 200

    @pytest.mark.asyncio
    async def test_retry_async_exhausted(self) -> None:
        """Test retry_async raises RetryExhaustedError."""

        async def always_fails() -> None:
            raise ValueError("Always fails")

        with pytest.raises(RetryExhaustedError) as exc_info:
            await retry_async(
                always_fails,
                RetryConfig(max_attempts=2, initial_delay=0.01),
            )

        assert exc_info.value.attempts == 2


class TestRetryExhaustedError:
    """Test suite for RetryExhaustedError exception."""

    def test_error_attributes(self) -> None:
        """Test RetryExhaustedError stores attempts and last_error."""
        original_error = ValueError("Original error")
        retry_error = RetryExhaustedError(attempts=5, last_error=original_error)

        assert retry_error.attempts == 5
        assert retry_error.last_error is original_error
        assert "5 attempts" in str(retry_error)
        assert "Original error" in str(retry_error)

    def test_error_chaining(self) -> None:
        """Test that RetryExhaustedError can be raised from original error."""
        original_error = ValueError("Root cause")

        try:
            raise RetryExhaustedError(attempts=3, last_error=original_error) from original_error
        except RetryExhaustedError as e:
            assert e.__cause__ is original_error


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_single_attempt_no_retry(self) -> None:
        """Test that max_attempts=1 means no retries."""
        call_count = 0

        @with_retry(RetryConfig(max_attempts=1))
        async def func() -> None:
            nonlocal call_count
            call_count += 1
            raise ValueError("Error")

        with pytest.raises(RetryExhaustedError):
            await func()

        assert call_count == 1  # Only one attempt, no retries

    @pytest.mark.asyncio
    async def test_zero_initial_delay(self) -> None:
        """Test that zero initial_delay works (immediate retry)."""
        call_count = 0

        @with_retry(
            RetryConfig(
                max_attempts=2,
                initial_delay=0.0,
                backoff_factor=1.0,
            )
        )
        async def func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First fails")
            return "success"

        result = await func()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_exception_with_all_base_exception_types(self) -> None:
        """Test retrying with Exception base class catches all."""

        @with_retry(
            RetryConfig(
                max_attempts=2,
                initial_delay=0.01,
                retriable_exceptions=(Exception,),  # Catches all Exception subclasses
            )
        )
        async def func() -> str:
            raise RuntimeError("Some error")

        with pytest.raises(RetryExhaustedError):
            await func()
