"""
API Documentation for Export Functionality

This module provides comprehensive API documentation for all export-related endpoints.
The documentation is automatically generated and available at /docs (Swagger UI).
"""

# Update main.py to include better API documentation

EXPORT_API_DESCRIPTION = """
# Export Functionality API

## Overview

The Export API provides comprehensive data export capabilities with support for multiple formats,
intelligent suggestions, and complete audit history.

## Supported Export Formats

| Format | Extension | MIME Type | Use Case |
|--------|-----------|-----------|----------|
| CSV | .csv | text/csv | Universal tabular data, Excel compatible |
| JSON | .json | application/json | Program-readable, preserves data structure |
| Excel | .xlsx | application/vnd...sheet | Data analysis, formatted tables |
| SQL | .sql | application/sql | Database migration, INSERT statements |

## Features

### 1. Direct Export
Export already-queried results in any supported format with customizable options.

### 2. Query and Export
Execute a SQL query and export results in one operation - perfect for automation.

### 3. Smart Suggestions
AI-powered analysis recommends the best export format based on:
- Query type (aggregation, JOIN, etc.)
- Result size (row count)
- Data complexity (column count)

### 4. Export History
Complete audit trail of all export operations with:
- SQL queries executed
- Export formats used
- File metadata and statistics
- Timestamps and performance metrics

## Authentication

Currently, no authentication is required. In production, implement:
- API keys
- OAuth 2.0
- JWT tokens

## Rate Limiting

Recommended limits:
- Export operations: 100 per hour per IP
- Query and export: 50 per hour per IP
- History queries: 200 per hour per IP

## Error Handling

All endpoints return standard HTTP status codes:
- 200: Success
- 400: Bad request (invalid parameters)
- 404: Resource not found (database connection)
- 500: Server error

Error responses follow this format:
```json
{
  "detail": "Error message description"
}
```

## Examples

See individual endpoint documentation for detailed examples.

## OpenAPI Specification

Full OpenAPI 3.0 specification available at `/openapi.json`.
Interactive documentation available at `/docs`.
"""


# Export endpoint tags for grouping
EXPORT_TAGS = [
    {
        "name": "exports",
        "description": "Export operations - convert query results to various formats",
    },
    {
        "name": "export-suggestions",
        "description": "AI-powered export format recommendations",
    },
    {
        "name": "export-history",
        "description": "Audit and track export operations",
    },
]


# Detailed endpoint documentation
EXPORT_ENDPOINT_DOCS = {
    "export_query_result": {
        "summary": "Export query result",
        "description": """
Export already-executed query results to the specified format.

**Use Case**: You have query results in memory and want to export them.

**Supported Formats**: CSV, JSON, Excel, SQL

**Options**:
- `delimiter`: CSV field delimiter (default: ",")
- `includeHeaders`: Include column headers (default: true)
- `prettyPrint`: Format JSON with indentation (default: true)
- `sheetName`: Excel worksheet name (default: "Sheet1")
- `tableName`: SQL table name for INSERT statements (default: "exported_data")

**Performance**:
- Small datasets (<10k rows): ~1-2 seconds
- Large datasets (>10k rows): ~5-10 seconds
- Maximum recommended: 1M rows
        """,
        "responses": {
            200: {
                "description": "File download",
                "content": {
                    "text/csv": {"example": "id,name\n1,Alice\n2,Bob"},
                    "application/json": {"example": {"columns": [], "rows": []}},
                },
            },
            400: {"description": "Invalid request (bad format, invalid options)"},
            404: {"description": "Database connection not found"},
        },
    },
    "query_and_export": {
        "summary": "Query and export in one operation",
        "description": """
Execute a SQL query and immediately export the results.

**Use Case**: Automation, scheduled reports, one-command exports.

**Benefits**:
- Single API call
- No intermediate storage
- Automatic history tracking
- Optimal for scripts and cron jobs

**Example Use Cases**:
1. Daily sales report: `SELECT * FROM sales WHERE date = CURRENT_DATE`
2. User export: `SELECT id, name, email FROM users WHERE active = true`
3. Analytics snapshot: `SELECT category, COUNT(*) FROM orders GROUP BY category`

**Timeout**: 60 seconds for query execution + export
        """,
        "responses": {
            200: {"description": "File download with query results"},
            400: {"description": "Invalid SQL or export options"},
            404: {"description": "Database connection not found"},
            500: {"description": "Query execution or export failed"},
        },
    },
    "suggest_export": {
        "summary": "Get AI-powered export format suggestion",
        "description": """
Analyze query results and recommend the optimal export format.

**Analysis Factors**:
1. **Row Count**: ≥100 rows → suggests export
2. **Query Type**:
   - Aggregation (SUM, AVG, COUNT) → Excel
   - Complex (JOIN, subqueries) → JSON
   - Simple SELECT → CSV
3. **Column Count**: >10 columns → Excel

**Response**:
- `shouldSuggest`: Boolean - whether to show suggestion
- `suggestedFormat`: Recommended format (csv, json, excel, sql)
- `reason`: Explanation for the recommendation
- `promptText`: User-friendly suggestion message

**Example Response**:
```json
{
  "shouldSuggest": true,
  "suggestedFormat": "excel",
  "reason": "查询返回了500行数据，检测到聚合函数，Excel格式更适合数据分析",
  "promptText": "需要将这次的查询结果导出为 Excel 文件吗？..."
}
```
        """,
    },
    "parse_nl_export_command": {
        "summary": "Parse natural language export command",
        "description": """
Convert natural language input to structured export command.

**Supported Commands** (Chinese & English):
- "导出为 CSV" / "export as CSV"
- "保存成 Excel" / "save as Excel"
- "导出上次查询" / "export last query"
- "把结果存为 JSON" / "save results as JSON"

**Response**:
- Success: `{"action": "export", "format": "csv", "target": "current"}`
- Not an export command: `{"action": null}`

**Target Values**:
- `current`: Export current/latest results
- `last`: Export previous query results

**Note**: This is a simplified implementation. For production, consider
integrating with OpenAI or other LLM for better natural language understanding.
        """,
    },
    "get_export_history": {
        "summary": "Get export history",
        "description": """
Retrieve audit history of export operations for a database.

**Use Cases**:
- Audit compliance
- Usage analytics
- Debugging
- User activity tracking

**Returned Information**:
- Export timestamp
- SQL query executed
- Export format used
- File metadata (name, size)
- Performance metrics (rows, time)

**Sorting**: Most recent exports first (DESC by created_at)

**Pagination**: Use `limit` parameter to control response size

**Future Enhancements**:
- Filter by date range
- Filter by format
- Filter by user (when auth is added)
- Search by SQL content
        """,
        "responses": {
            200: {
                "description": "List of export history entries",
                "content": {
                    "application/json": {
                        "example": [
                            {
                                "id": 1,
                                "databaseName": "mydb",
                                "sql": "SELECT * FROM users",
                                "exportFormat": "csv",
                                "fileName": "export_20260205_120000.csv",
                                "fileSizeBytes": 1024,
                                "rowCount": 100,
                                "exportTimeMs": 150,
                                "createdAt": "2026-02-05T12:00:00",
                            }
                        ]
                    }
                },
            }
        },
    },
}


# Code examples for each endpoint
EXPORT_CODE_EXAMPLES = {
    "curl": {
        "export": """
# Export query results
curl -X POST http://localhost:8000/api/v1/dbs/mydb/export \\
  -H "Content-Type: application/json" \\
  -d '{
    "columns": [{"name": "id", "dataType": "integer"}],
    "rows": [{"id": 1}, {"id": 2}],
    "format": "csv"
  }' \\
  --output export.csv
        """,
        "query_and_export": """
# Query and export in one operation
curl -X POST http://localhost:8000/api/v1/dbs/mydb/query-and-export \\
  -H "Content-Type: application/json" \\
  -d '{
    "sql": "SELECT * FROM users LIMIT 100",
    "format": "excel",
    "options": {
      "sheetName": "Users"
    }
  }' \\
  --output users.xlsx
        """,
        "suggest": """
# Get export suggestion
curl -X POST http://localhost:8000/api/v1/dbs/mydb/export/suggest \\
  -H "Content-Type: application/json" \\
  -d '{
    "sql": "SELECT name, SUM(amount) FROM sales GROUP BY name",
    "columns": [{"name": "name", "dataType": "varchar"}],
    "rowCount": 500
  }'
        """,
        "history": """
# Get export history
curl http://localhost:8000/api/v1/dbs/mydb/exports?limit=10
        """,
    },
    "python": {
        "export": """
import requests

response = requests.post(
    "http://localhost:8000/api/v1/dbs/mydb/export",
    json={
        "columns": [{"name": "id", "dataType": "integer"}],
        "rows": [{"id": 1}, {"id": 2}],
        "format": "csv"
    }
)

with open("export.csv", "wb") as f:
    f.write(response.content)
        """,
        "query_and_export": """
import requests

response = requests.post(
    "http://localhost:8000/api/v1/dbs/mydb/query-and-export",
    json={
        "sql": "SELECT * FROM users LIMIT 100",
        "format": "excel"
    }
)

with open("users.xlsx", "wb") as f:
    f.write(response.content)
        """,
    },
    "javascript": {
        "export": """
// Using fetch API
const response = await fetch(
  'http://localhost:8000/api/v1/dbs/mydb/export',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      columns: [{ name: 'id', dataType: 'integer' }],
      rows: [{ id: 1 }, { id: 2 }],
      format: 'csv'
    })
  }
);

const blob = await response.blob();
const url = URL.createObjectURL(blob);
const link = document.createElement('a');
link.href = url;
link.download = 'export.csv';
link.click();
        """,
    },
}
