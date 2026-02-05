"""Unit tests for ExecutorManager.

This module tests the ExecutorManager class which provides multi-database
executor management and routing functionality.
"""

import pytest
from unittest.mock import Mock

from src.services.sql_executor import ExecutorManager, SQLExecutor


class TestExecutorManager:
    """Test suite for ExecutorManager."""

    @pytest.fixture
    def mock_executor_main(self):
        """Create mock executor for 'main' database."""
        return Mock(spec=SQLExecutor)

    @pytest.fixture
    def mock_executor_analytics(self):
        """Create mock executor for 'analytics' database."""
        return Mock(spec=SQLExecutor)

    @pytest.fixture
    def executor_manager(self, mock_executor_main, mock_executor_analytics):
        """Create ExecutorManager with two databases."""
        executors = {
            "main": mock_executor_main,
            "analytics": mock_executor_analytics,
        }
        return ExecutorManager(executors, default_database="main")

    def test_init_with_valid_config(self, mock_executor_main, mock_executor_analytics):
        """Test initialization with valid configuration."""
        executors = {
            "main": mock_executor_main,
            "analytics": mock_executor_analytics,
        }

        manager = ExecutorManager(executors, default_database="main")

        assert manager.default_database == "main"
        assert manager.list_databases() == ["main", "analytics"]

    def test_init_with_empty_executors_raises(self):
        """Test initialization with empty executors raises ValueError."""
        with pytest.raises(ValueError, match="At least one executor must be provided"):
            ExecutorManager({}, default_database="main")

    def test_init_with_invalid_default_raises(self, mock_executor_main):
        """Test initialization with invalid default database raises ValueError."""
        executors = {"main": mock_executor_main}

        with pytest.raises(
            ValueError, match="Default database 'invalid' not found"
        ):
            ExecutorManager(executors, default_database="invalid")

    def test_get_executor_with_none_returns_default(
        self, executor_manager, mock_executor_main
    ):
        """Test get_executor with None returns default executor."""
        executor = executor_manager.get_executor(None)

        assert executor is mock_executor_main

    def test_get_executor_with_explicit_name(
        self, executor_manager, mock_executor_analytics
    ):
        """Test get_executor with explicit database name."""
        executor = executor_manager.get_executor("analytics")

        assert executor is mock_executor_analytics

    def test_get_executor_with_invalid_name_raises(self, executor_manager):
        """Test get_executor with invalid database name raises ValueError."""
        with pytest.raises(ValueError, match="Database 'invalid' not found"):
            executor_manager.get_executor("invalid")

    def test_list_databases_returns_all_names(self, executor_manager):
        """Test list_databases returns all database names."""
        databases = executor_manager.list_databases()

        assert set(databases) == {"main", "analytics"}
        assert len(databases) == 2

    def test_default_database_property(self, executor_manager):
        """Test default_database property returns correct name."""
        assert executor_manager.default_database == "main"

    def test_single_database_configuration(self, mock_executor_main):
        """Test ExecutorManager with single database."""
        executors = {"main": mock_executor_main}
        manager = ExecutorManager(executors, default_database="main")

        assert manager.list_databases() == ["main"]
        assert manager.get_executor() is mock_executor_main
        assert manager.get_executor("main") is mock_executor_main


class TestExecutorManagerErrorMessages:
    """Test ExecutorManager error messages are helpful."""

    def test_invalid_database_error_shows_available(self):
        """Test error message includes list of available databases."""
        executors = {
            "main": Mock(spec=SQLExecutor),
            "analytics": Mock(spec=SQLExecutor),
        }
        manager = ExecutorManager(executors, default_database="main")

        with pytest.raises(ValueError) as exc_info:
            manager.get_executor("invalid")

        error_msg = str(exc_info.value)
        assert "invalid" in error_msg
        assert "Available databases: ['main', 'analytics']" in error_msg

    def test_invalid_default_error_shows_available(self):
        """Test initialization error shows available databases."""
        executors = {
            "main": Mock(spec=SQLExecutor),
            "analytics": Mock(spec=SQLExecutor),
        }

        with pytest.raises(ValueError) as exc_info:
            ExecutorManager(executors, default_database="invalid")

        error_msg = str(exc_info.value)
        assert "invalid" in error_msg
        assert "Available databases: ['main', 'analytics']" in error_msg
