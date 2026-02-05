"""Unit tests for export functionality."""

import pytest
from app.export.base import ExportFormat, ExportOptions
from app.export.csv_exporter import CSVExporter
from app.export.json_exporter import JSONExporter
from app.export.excel_exporter import ExcelExporter
from app.export.sql_exporter import SQLExporter
from app.export.registry import export_registry


@pytest.mark.asyncio
async def test_csv_export_basic():
    """Test basic CSV export."""
    exporter = CSVExporter()
    columns = [{"name": "id", "dataType": "integer"}, {"name": "name", "dataType": "varchar"}]
    rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    options = ExportOptions(format=ExportFormat.CSV)

    result = await exporter.export(columns, rows, options)

    assert result.row_count == 2
    assert result.file_name.endswith(".csv")
    assert b"id" in result.file_data  # Header
    assert b"Alice" in result.file_data
    assert b"Bob" in result.file_data


@pytest.mark.asyncio
async def test_csv_export_special_chars():
    """Test CSV export with special characters."""
    exporter = CSVExporter()
    columns = [{"name": "name", "dataType": "varchar"}]
    rows = [{"name": "Alice, Bob"}, {"name": 'John "Doe"'}]
    options = ExportOptions(format=ExportFormat.CSV)

    result = await exporter.export(columns, rows, options)

    # Verify proper quoting
    content = result.file_data.decode("utf-8")
    assert '"Alice, Bob"' in content
    assert 'John ""Doe""' in content or '"John ""Doe"""' in content


@pytest.mark.asyncio
async def test_csv_export_none_values():
    """Test CSV export with None values."""
    exporter = CSVExporter()
    columns = [{"name": "id", "dataType": "integer"}, {"name": "value", "dataType": "varchar"}]
    rows = [{"id": 1, "value": None}, {"id": 2, "value": "test"}]
    options = ExportOptions(format=ExportFormat.CSV)

    result = await exporter.export(columns, rows, options)

    assert result.row_count == 2
    content = result.file_data.decode("utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 3  # Header + 2 rows


@pytest.mark.asyncio
async def test_json_export_basic():
    """Test basic JSON export."""
    exporter = JSONExporter()
    columns = [{"name": "id", "dataType": "integer"}]
    rows = [{"id": 1}, {"id": 2}]
    options = ExportOptions(format=ExportFormat.JSON)

    result = await exporter.export(columns, rows, options)

    assert result.row_count == 2
    assert result.file_name.endswith(".json")
    assert b'"columns"' in result.file_data
    assert b'"rows"' in result.file_data


@pytest.mark.asyncio
async def test_json_export_pretty_print():
    """Test JSON export with pretty printing."""
    exporter = JSONExporter()
    columns = [{"name": "id", "dataType": "integer"}]
    rows = [{"id": 1}]
    options = ExportOptions(format=ExportFormat.JSON, pretty_print=True)

    result = await exporter.export(columns, rows, options)

    content = result.file_data.decode("utf-8")
    # Pretty print should have indentation
    assert "  " in content


@pytest.mark.asyncio
async def test_excel_export_basic():
    """Test basic Excel export."""
    exporter = ExcelExporter()
    columns = [{"name": "id", "dataType": "integer"}, {"name": "name", "dataType": "varchar"}]
    rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    options = ExportOptions(format=ExportFormat.EXCEL)

    result = await exporter.export(columns, rows, options)

    assert result.row_count == 2
    assert result.file_name.endswith(".xlsx")
    assert result.mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert result.file_size_bytes > 0


@pytest.mark.asyncio
async def test_sql_export_basic():
    """Test basic SQL export."""
    exporter = SQLExporter()
    columns = [{"name": "id", "dataType": "integer"}, {"name": "name", "dataType": "varchar"}]
    rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    options = ExportOptions(format=ExportFormat.SQL, table_name="users")

    result = await exporter.export(columns, rows, options)

    assert result.row_count == 2
    assert result.file_name.endswith(".sql")
    content = result.file_data.decode("utf-8")
    assert "INSERT INTO users" in content
    assert "'Alice'" in content
    assert "'Bob'" in content


@pytest.mark.asyncio
async def test_sql_export_special_values():
    """Test SQL export with special values."""
    exporter = SQLExporter()
    columns = [
        {"name": "id", "dataType": "integer"},
        {"name": "name", "dataType": "varchar"},
        {"name": "active", "dataType": "boolean"},
    ]
    rows = [
        {"id": 1, "name": "O'Brien", "active": True},
        {"id": 2, "name": None, "active": False},
    ]
    options = ExportOptions(format=ExportFormat.SQL, table_name="users")

    result = await exporter.export(columns, rows, options)

    content = result.file_data.decode("utf-8")
    assert "O''Brien" in content  # Escaped quote
    assert "NULL" in content  # None value
    assert "TRUE" in content  # Boolean true
    assert "FALSE" in content  # Boolean false


def test_export_registry():
    """Test export registry."""
    # Test CSV
    csv_exporter = export_registry.get_exporter(ExportFormat.CSV)
    assert isinstance(csv_exporter, CSVExporter)

    # Test JSON
    json_exporter = export_registry.get_exporter(ExportFormat.JSON)
    assert isinstance(json_exporter, JSONExporter)

    # Test Excel
    excel_exporter = export_registry.get_exporter(ExportFormat.EXCEL)
    assert isinstance(excel_exporter, ExcelExporter)

    # Test SQL
    sql_exporter = export_registry.get_exporter(ExportFormat.SQL)
    assert isinstance(sql_exporter, SQLExporter)

    # Test list formats
    formats = export_registry.list_formats()
    assert "csv" in formats
    assert "json" in formats
    assert "excel" in formats
    assert "sql" in formats


def test_export_registry_invalid_format():
    """Test export registry with invalid format."""
    with pytest.raises(ValueError, match="Unsupported export format"):
        export_registry.get_exporter("invalid")


@pytest.mark.asyncio
async def test_exporter_file_extension():
    """Test file extensions for all exporters."""
    assert CSVExporter().get_file_extension() == "csv"
    assert JSONExporter().get_file_extension() == "json"
    assert ExcelExporter().get_file_extension() == "xlsx"
    assert SQLExporter().get_file_extension() == "sql"


@pytest.mark.asyncio
async def test_exporter_mime_types():
    """Test MIME types for all exporters."""
    assert CSVExporter().get_mime_type() == "text/csv"
    assert JSONExporter().get_mime_type() == "application/json"
    assert (
        ExcelExporter().get_mime_type()
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert SQLExporter().get_mime_type() == "application/sql"


@pytest.mark.asyncio
async def test_exporter_streaming_support():
    """Test streaming support flags."""
    assert CSVExporter().supports_streaming() is True
    assert JSONExporter().supports_streaming() is False
    assert ExcelExporter().supports_streaming() is True
    assert SQLExporter().supports_streaming() is True
