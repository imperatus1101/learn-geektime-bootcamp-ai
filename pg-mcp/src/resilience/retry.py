"""Retry mechanism with exponential backoff for fault tolerance.

This module provides retry decorators and utilities for handling transient
failures in asynchronous operations. It implements exponential backoff strategy
with configurable parameters.
"""

import asyncio
import functools
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


class RetryConfig:
    """Configuration for retry behavior with exponential backoff.

    Example:
        >>> config = RetryConfig(
        ...     max_attempts=3,
        ...     initial_delay=1.0,
        ...     backoff_factor=2.0,
        ...     max_delay=60.0,
        ...     retriable_exceptions=(TimeoutError, ConnectionError),
        ... )
    """

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        retriable_exceptions: tuple[type[Exception], ...] = (Exception,),
    ) -> None:
        """Initialize retry configuration.

        Args:
            max_attempts: Maximum number of attempts (including initial attempt).
            initial_delay: Initial delay between retries in seconds.
            backoff_factor: Multiplier for exponential backoff (delay *= factor).
            max_delay: Maximum delay between retries in seconds.
            retriable_exceptions: Tuple of exception types that should trigger retry.

        Raises:
            ValueError: If parameters are invalid.
        """
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if initial_delay < 0:
            raise ValueError("initial_delay must be >= 0")
        if backoff_factor < 1.0:
            raise ValueError("backoff_factor must be >= 1.0")
        if max_delay < initial_delay:
            raise ValueError("max_delay must be >= initial_delay")

        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.retriable_exceptions = retriable_exceptions

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt using exponential backoff.

        Formula: min(initial_delay * (backoff_factor ** attempt), max_delay)

        Args:
            attempt: Attempt number (0-indexed, 0 = first retry).

        Returns:
            Delay in seconds before next retry.

        Example:
            >>> config = RetryConfig(initial_delay=1.0, backoff_factor=2.0, max_delay=10.0)
            >>> config.calculate_delay(0)  # 1.0
            >>> config.calculate_delay(1)  # 2.0
            >>> config.calculate_delay(2)  # 4.0
            >>> config.calculate_delay(3)  # 8.0
            >>> config.calculate_delay(4)  # 10.0 (capped at max_delay)
        """
        delay = self.initial_delay * (self.backoff_factor**attempt)
        return min(delay, self.max_delay)


class RetryExhaustedError(Exception):
    """Exception raised when all retry attempts are exhausted.

    Attributes:
        attempts: Number of attempts made.
        last_error: The final exception that caused failure.
    """

    def __init__(self, attempts: int, last_error: Exception) -> None:
        """Initialize retry exhausted error.

        Args:
            attempts: Number of attempts made before giving up.
            last_error: The exception from the final attempt.
        """
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Retry exhausted after {attempts} attempts. Last error: {last_error}"
        )


def with_retry(config: RetryConfig) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator for adding retry logic to async functions.

    Automatically retries the decorated function on failure using exponential
    backoff. Only retries exceptions specified in config.retriable_exceptions.

    Args:
        config: Retry configuration.

    Returns:
        Decorator function that adds retry logic.

    Example:
        >>> @with_retry(RetryConfig(max_attempts=3, initial_delay=1.0))
        >>> async def call_api():
        ...     # API call that might fail
        ...     return await client.get("/data")

        >>> # Use with specific exceptions
        >>> @with_retry(RetryConfig(
        ...     max_attempts=3,
        ...     retriable_exceptions=(TimeoutError, ConnectionError)
        ... ))
        >>> async def fetch_data():
        ...     return await unstable_service()
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(config.max_attempts):
                try:
                    # Attempt the operation
                    result = await func(*args, **kwargs)

                    # Log success if this was a retry
                    if attempt > 0:
                        logger.info(
                            "retry_succeeded",
                            function=func.__name__,
                            attempt=attempt + 1,
                            total_attempts=config.max_attempts,
                        )

                    return result

                except config.retriable_exceptions as e:
                    last_exception = e
                    is_last_attempt = attempt == config.max_attempts - 1

                    if is_last_attempt:
                        # No more retries, log and raise
                        logger.error(
                            "retry_exhausted",
                            function=func.__name__,
                            attempts=config.max_attempts,
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                        raise RetryExhaustedError(
                            attempts=config.max_attempts,
                            last_error=e,
                        ) from e

                    # Calculate delay and wait
                    delay = config.calculate_delay(attempt)

                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_attempts=config.max_attempts,
                        delay=delay,
                        error=str(e),
                        error_type=type(e).__name__,
                    )

                    await asyncio.sleep(delay)

            # This should never be reached, but satisfies type checker
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


async def retry_async(
    func: Callable[..., Awaitable[T]],
    config: RetryConfig,
    *args: Any,
    **kwargs: Any,
) -> T:
    """Functional retry helper for async functions.

    Alternative to decorator when you need to retry a function call
    without decorating the function itself.

    Args:
        func: Async function to retry.
        config: Retry configuration.
        *args: Positional arguments to pass to func.
        **kwargs: Keyword arguments to pass to func.

    Returns:
        Result from successful function call.

    Raises:
        RetryExhaustedError: If all retry attempts fail.

    Example:
        >>> async def fetch_data(url: str) -> dict:
        ...     return await http_client.get(url)
        >>>
        >>> result = await retry_async(
        ...     fetch_data,
        ...     RetryConfig(max_attempts=3, initial_delay=1.0),
        ...     "https://api.example.com/data"
        ... )
    """

    @with_retry(config)
    async def _wrapper() -> T:
        return await func(*args, **kwargs)

    return await _wrapper()
