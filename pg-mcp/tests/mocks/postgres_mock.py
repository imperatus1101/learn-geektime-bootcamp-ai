"""Mock PostgreSQL connections for deterministic testing.

This module provides mock implementations of asyncpg connections and pools,
allowing database tests to run without a real PostgreSQL instance.
"""

from typing import Any


class MockPostgresPool:
    """Mock PostgreSQL connection pool.

    This mock simulates an asyncpg.Pool, providing predefined query results
    and connection management without requiring a real database.

    Example:
        >>> pool = MockPostgresPool()
        >>> pool.set_query_result("SELECT * FROM users", [{"id": 1, "name": "Alice"}])
        >>> result = await pool.fetch("SELECT * FROM users")
        >>> print(result)
        [{'id': 1, 'name': 'Alice'}]
    """

    def __init__(self) -> None:
        """Initialize mock PostgreSQL pool."""
        self._closed = False
        self._query_results: dict[str, list[dict[str, Any]]] = {}
        self._size = 10
        self._min_size = 5
        self._max_size = 20

    def set_query_result(
        self,
        sql_pattern: str,
        result: list[dict[str, Any]],
    ) -> None:
        """Set a predefined result for a SQL pattern.

        Args:
            sql_pattern: SQL substring to match (case-insensitive).
            result: List of row dictionaries to return.
        """
        self._query_results[sql_pattern.lower()] = result

    async def fetch(
        self,
        sql: str,
        *args: Any,
        timeout: float | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a query and return results.

        Args:
            sql: SQL query to execute.
            *args: Query parameters.
            timeout: Optional timeout.

        Returns:
            List of row dictionaries.

        Raises:
            RuntimeError: If pool is closed.
        """
        if self._closed:
            raise RuntimeError("Pool is closed")

        # Normalize SQL for matching
        sql_lower = sql.lower().strip()

        # Match against predefined patterns
        for pattern, result in self._query_results.items():
            if pattern in sql_lower:
                return result

        # Default empty result if no match
        return []

    async def fetchrow(
        self,
        sql: str,
        *args: Any,
        timeout: float | None = None,
    ) -> dict[str, Any] | None:
        """Execute a query and return the first row.

        Args:
            sql: SQL query to execute.
            *args: Query parameters.
            timeout: Optional timeout.

        Returns:
            First row dictionary or None if no results.
        """
        results = await self.fetch(sql, *args, timeout=timeout)
        return results[0] if results else None

    async def execute(
        self,
        sql: str,
        *args: Any,
        timeout: float | None = None,
    ) -> str:
        """Execute a SQL command.

        Args:
            sql: SQL command to execute.
            *args: Query parameters.
            timeout: Optional timeout.

        Returns:
            Status string (e.g., "SELECT 5").
        """
        if self._closed:
            raise RuntimeError("Pool is closed")

        # For mock, just return a success status
        results = await self.fetch(sql, *args, timeout=timeout)
        return f"SELECT {len(results)}"

    def acquire(self) -> "MockPostgresConnection":
        """Acquire a connection from the pool (sync context manager support).

        Returns:
            MockPostgresConnection.
        """
        return MockPostgresConnection(self)

    async def __aenter__(self) -> "MockPostgresPool":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the connection pool."""
        self._closed = True
        self._size = 0

    def get_size(self) -> int:
        """Get the current pool size.

        Returns:
            Number of connections in the pool.
        """
        return self._size if not self._closed else 0

    def get_min_size(self) -> int:
        """Get the minimum pool size.

        Returns:
            Minimum number of connections.
        """
        return self._min_size

    def get_max_size(self) -> int:
        """Get the maximum pool size.

        Returns:
            Maximum number of connections.
        """
        return self._max_size

    def is_closed(self) -> bool:
        """Check if the pool is closed.

        Returns:
            True if closed, False otherwise.
        """
        return self._closed


class MockPostgresConnection:
    """Mock PostgreSQL connection.

    This mock simulates an asyncpg.Connection, delegating to the parent pool
    for query execution.
    """

    def __init__(self, pool: MockPostgresPool) -> None:
        """Initialize mock connection.

        Args:
            pool: Parent pool instance.
        """
        self._pool = pool
        self._closed = False

    async def fetch(
        self,
        sql: str,
        *args: Any,
        timeout: float | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a query and return results.

        Args:
            sql: SQL query to execute.
            *args: Query parameters.
            timeout: Optional timeout.

        Returns:
            List of row dictionaries.
        """
        if self._closed:
            raise RuntimeError("Connection is closed")
        return await self._pool.fetch(sql, *args, timeout=timeout)

    async def fetchrow(
        self,
        sql: str,
        *args: Any,
        timeout: float | None = None,
    ) -> dict[str, Any] | None:
        """Execute a query and return the first row.

        Args:
            sql: SQL query to execute.
            *args: Query parameters.
            timeout: Optional timeout.

        Returns:
            First row dictionary or None if no results.
        """
        if self._closed:
            raise RuntimeError("Connection is closed")
        return await self._pool.fetchrow(sql, *args, timeout=timeout)

    async def execute(
        self,
        sql: str,
        *args: Any,
        timeout: float | None = None,
    ) -> str:
        """Execute a SQL command.

        Args:
            sql: SQL command to execute.
            *args: Query parameters.
            timeout: Optional timeout.

        Returns:
            Status string.
        """
        if self._closed:
            raise RuntimeError("Connection is closed")
        return await self._pool.execute(sql, *args, timeout=timeout)

    async def close(self) -> None:
        """Close the connection."""
        self._closed = True

    async def __aenter__(self) -> "MockPostgresConnection":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
