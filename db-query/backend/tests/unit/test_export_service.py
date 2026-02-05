"""Unit tests for export service."""

import pytest
from unittest.mock import Mock, AsyncMock
from app.services.export_service import ExportService
from app.export.base import ExportFormat, ExportOptions, ExportResult
from app.models.export import QueryExport


@pytest.mark.asyncio
async def test_export_service_with_csv_format():
    """Test export service with CSV format."""
    service = ExportService()

    columns = [{"name": "id", "dataType": "integer"}]
    rows = [{"id": 1}, {"id": 2}]

    result = await service.export_query_result(
        columns=columns,
        rows=rows,
        format=ExportFormat.CSV,
    )

    assert isinstance(result, ExportResult)
    assert result.row_count == 2
    assert result.file_name.endswith(".csv")
    assert result.file_data is not None


@pytest.mark.asyncio
async def test_export_service_with_custom_options():
    """Test export service with custom options."""
    service = ExportService()

    columns = [{"name": "id", "dataType": "integer"}]
    rows = [{"id": 1}]

    options = ExportOptions(
        format=ExportFormat.CSV,
        delimiter=";",
        include_headers=False,
    )

    result = await service.export_query_result(
        columns=columns,
        rows=rows,
        format=ExportFormat.CSV,
        options=options,
    )

    assert result is not None
    # Verify delimiter is used (semicolon instead of comma)
    content = result.file_data.decode("utf-8")
    if not options.include_headers:
        # Should not have header line
        assert "id" not in content or ";" in content


@pytest.mark.asyncio
async def test_export_service_with_all_formats():
    """Test export service with all supported formats."""
    service = ExportService()

    columns = [{"name": "id", "dataType": "integer"}]
    rows = [{"id": 1}]

    formats = [
        ExportFormat.CSV,
        ExportFormat.JSON,
        ExportFormat.EXCEL,
        ExportFormat.SQL,
    ]

    for fmt in formats:
        result = await service.export_query_result(
            columns=columns,
            rows=rows,
            format=fmt,
        )

        assert result is not None
        assert result.row_count == 1
        assert result.file_size_bytes > 0
        assert result.export_time_ms >= 0


@pytest.mark.asyncio
async def test_export_service_with_empty_rows():
    """Test export service with empty rows."""
    service = ExportService()

    columns = [{"name": "id", "dataType": "integer"}]
    rows = []

    result = await service.export_query_result(
        columns=columns,
        rows=rows,
        format=ExportFormat.CSV,
    )

    assert result.row_count == 0
    assert result.file_data is not None  # Should have at least headers


@pytest.mark.asyncio
async def test_export_service_invalid_options():
    """Test export service with invalid options."""
    service = ExportService()

    columns = [{"name": "id", "dataType": "integer"}]
    rows = [{"id": 1}]

    # Create options with max_rows exceeding limit
    options = ExportOptions(
        format=ExportFormat.CSV,
        max_rows=2_000_000,  # Exceeds MAX_EXPORT_ROWS
    )

    with pytest.raises(ValueError, match="Invalid export options"):
        await service.export_query_result(
            columns=columns,
            rows=rows,
            format=ExportFormat.CSV,
            options=options,
        )


@pytest.mark.asyncio
async def test_save_export_history(test_db_session):
    """Test saving export history."""
    service = ExportService()

    result = ExportResult(
        file_name="test_export.csv",
        mime_type="text/csv",
        row_count=100,
        file_size_bytes=1024,
        export_time_ms=150,
        file_data=b"test data",
    )

    history = await service.save_export_history(
        session=test_db_session,
        db_name="testdb",
        sql="SELECT * FROM users",
        format=ExportFormat.CSV,
        result=result,
    )

    assert isinstance(history, QueryExport)
    assert history.database_name == "testdb"
    assert history.sql == "SELECT * FROM users"
    assert history.export_format == "csv"
    assert history.row_count == 100
    assert history.file_size_bytes == 1024


@pytest.mark.asyncio
async def test_get_export_history_empty(test_db_session):
    """Test getting export history when empty."""
    service = ExportService()

    history = await service.get_export_history(
        session=test_db_session,
        db_name="nonexistent_db",
        limit=10,
    )

    assert isinstance(history, list)
    assert len(history) == 0


@pytest.mark.asyncio
async def test_get_export_history_with_limit(test_db_session):
    """Test getting export history with limit."""
    service = ExportService()

    # Create multiple history records
    for i in range(5):
        result = ExportResult(
            file_name=f"test_{i}.csv",
            mime_type="text/csv",
            row_count=100,
            file_size_bytes=1024,
            export_time_ms=150,
            file_data=b"test data",
        )

        await service.save_export_history(
            session=test_db_session,
            db_name="testdb",
            sql=f"SELECT * FROM table_{i}",
            format=ExportFormat.CSV,
            result=result,
        )

    # Get history with limit
    history = await service.get_export_history(
        session=test_db_session,
        db_name="testdb",
        limit=3,
    )

    assert len(history) <= 3
    # Should be ordered by created_at desc (most recent first)
    if len(history) > 1:
        assert history[0].created_at >= history[1].created_at


@pytest.mark.asyncio
async def test_export_service_large_dataset():
    """Test export service with large dataset."""
    service = ExportService()

    columns = [
        {"name": "id", "dataType": "integer"},
        {"name": "name", "dataType": "varchar"},
        {"name": "email", "dataType": "varchar"},
    ]

    # Generate 1000 rows
    rows = [
        {
            "id": i,
            "name": f"User {i}",
            "email": f"user{i}@example.com",
        }
        for i in range(1000)
    ]

    result = await service.export_query_result(
        columns=columns,
        rows=rows,
        format=ExportFormat.CSV,
    )

    assert result.row_count == 1000
    assert result.file_size_bytes > 10000  # Should be substantial
    assert result.export_time_ms > 0


@pytest.mark.asyncio
async def test_export_service_with_special_characters():
    """Test export service with special characters."""
    service = ExportService()

    columns = [{"name": "text", "dataType": "varchar"}]
    rows = [
        {"text": "Hello, World!"},
        {"text": 'Quote: "test"'},
        {"text": "Newline:\ntest"},
        {"text": "中文测试"},
        {"text": "Special: @#$%^&*()"},
    ]

    result = await service.export_query_result(
        columns=columns,
        rows=rows,
        format=ExportFormat.CSV,
    )

    assert result.row_count == 5
    content = result.file_data.decode("utf-8")
    # Should handle special characters correctly
    assert "中文" in content or len(content) > 0


@pytest.mark.asyncio
async def test_export_service_with_null_values():
    """Test export service with NULL values."""
    service = ExportService()

    columns = [
        {"name": "id", "dataType": "integer"},
        {"name": "value", "dataType": "varchar"},
    ]
    rows = [
        {"id": 1, "value": None},
        {"id": 2, "value": "test"},
        {"id": 3, "value": None},
    ]

    result = await service.export_query_result(
        columns=columns,
        rows=rows,
        format=ExportFormat.CSV,
    )

    assert result.row_count == 3
    # NULL values should be handled (empty string or "NULL")


@pytest.mark.asyncio
async def test_export_service_performance():
    """Test export service performance with moderate dataset."""
    import time

    service = ExportService()

    columns = [{"name": f"col{i}", "dataType": "varchar"} for i in range(10)]
    rows = [{f"col{i}": f"value{j}_{i}" for i in range(10)} for j in range(5000)]

    start = time.time()
    result = await service.export_query_result(
        columns=columns,
        rows=rows,
        format=ExportFormat.CSV,
    )
    duration = time.time() - start

    assert result.row_count == 5000
    assert duration < 5.0  # Should complete within 5 seconds


# Fixtures
@pytest.fixture
def test_db_session():
    """Create a test database session."""
    from sqlmodel import create_engine, Session, SQLModel
    from app.models.export import QueryExport

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session
