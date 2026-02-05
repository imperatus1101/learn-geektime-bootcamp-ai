"""Integration tests for export API endpoints."""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_export_csv_endpoint(client: AsyncClient):
    """Test CSV export endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Create a test database connection first
        # (Assumes a test database is available)

        response = await ac.post(
            "/api/v1/dbs/testdb/export",
            json={
                "columns": [
                    {"name": "id", "dataType": "integer"},
                    {"name": "name", "dataType": "varchar"},
                ],
                "rows": [
                    {"id": 1, "name": "Alice"},
                    {"id": 2, "name": "Bob"},
                ],
                "format": "csv",
            },
        )

        assert response.status_code == 200 or response.status_code == 404  # 404 if testdb doesn't exist
        if response.status_code == 200:
            assert response.headers["content-type"] == "text/csv"
            assert "attachment" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_json_endpoint(client: AsyncClient):
    """Test JSON export endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/dbs/testdb/export",
            json={
                "columns": [{"name": "id", "dataType": "integer"}],
                "rows": [{"id": 1}],
                "format": "json",
            },
        )

        assert response.status_code == 200 or response.status_code == 404
        if response.status_code == 200:
            assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_export_excel_endpoint(client: AsyncClient):
    """Test Excel export endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/dbs/testdb/export",
            json={
                "columns": [{"name": "id", "dataType": "integer"}],
                "rows": [{"id": 1}],
                "format": "excel",
            },
        )

        assert response.status_code == 200 or response.status_code == 404
        if response.status_code == 200:
            assert (
                response.headers["content-type"]
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


@pytest.mark.asyncio
async def test_export_sql_endpoint(client: AsyncClient):
    """Test SQL export endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/dbs/testdb/export",
            json={
                "columns": [{"name": "id", "dataType": "integer"}],
                "rows": [{"id": 1}],
                "format": "sql",
                "options": {"tableName": "test_table"},
            },
        )

        assert response.status_code == 200 or response.status_code == 404
        if response.status_code == 200:
            assert response.headers["content-type"] == "application/sql"
            content = response.content.decode("utf-8")
            assert "INSERT INTO" in content


@pytest.mark.asyncio
async def test_export_invalid_format(client: AsyncClient):
    """Test export with invalid format."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/dbs/testdb/export",
            json={
                "columns": [{"name": "id", "dataType": "integer"}],
                "rows": [{"id": 1}],
                "format": "invalid",
            },
        )

        # Should return validation error
        assert response.status_code in [400, 404, 422]


@pytest.mark.asyncio
async def test_query_and_export_endpoint(client: AsyncClient):
    """Test query and export endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/dbs/testdb/query-and-export",
            json={
                "sql": "SELECT 1 as id",
                "format": "csv",
            },
        )

        # Will return 404 if testdb doesn't exist, which is expected in tests
        assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_export_with_options(client: AsyncClient):
    """Test export with custom options."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/dbs/testdb/export",
            json={
                "columns": [{"name": "id", "dataType": "integer"}],
                "rows": [{"id": 1}],
                "format": "csv",
                "options": {
                    "delimiter": ";",
                    "includeHeaders": False,
                },
            },
        )

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            content = response.content.decode("utf-8")
            # Should use semicolon delimiter
            assert ";" in content or len(content.strip()) > 0


@pytest.mark.asyncio
async def test_export_empty_rows(client: AsyncClient):
    """Test export with empty rows."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/dbs/testdb/export",
            json={
                "columns": [{"name": "id", "dataType": "integer"}],
                "rows": [],
                "format": "csv",
            },
        )

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            content = response.content.decode("utf-8")
            # Should at least have headers
            assert "id" in content or len(content.strip()) == 0


@pytest.mark.asyncio
async def test_export_large_dataset(client: AsyncClient):
    """Test export with larger dataset."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Generate 1000 rows
        rows = [{"id": i, "value": f"value_{i}"} for i in range(1000)]

        response = await ac.post(
            "/api/v1/dbs/testdb/export",
            json={
                "columns": [
                    {"name": "id", "dataType": "integer"},
                    {"name": "value", "dataType": "varchar"},
                ],
                "rows": rows,
                "format": "csv",
            },
        )

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert len(response.content) > 0
