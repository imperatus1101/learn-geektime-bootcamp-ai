# Database Query Tool Backend

FastAPI backend for the Database Query Tool application.

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Create `.env` file from `.env.example`:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

3. Run database migrations:
```bash
alembic upgrade head
```

4. Start the development server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`
API documentation at `http://localhost:8000/docs`

## Features

### Query Execution
- Connect to PostgreSQL, MySQL, and SQLite databases
- Execute SQL queries with syntax validation
- Real-time query results with column metadata
- Natural language to SQL conversion (AI-powered)

### Export Functionality
- **Multiple formats**: CSV, JSON, Excel (.xlsx), SQL (INSERT statements)
- **Smart suggestions**: AI-powered format recommendations based on query analysis
- **Natural language**: Support for Chinese and English export commands
- **Export history**: Complete audit trail with metadata tracking
- **Query & Export**: One-step query execution and export
- **Performance**: Optimized for large datasets with streaming support

See [USER_GUIDE.md](../USER_GUIDE.md) for detailed usage instructions.

## Project Structure

- `app/` - Application code
  - `main.py` - FastAPI application entry point
  - `config.py` - Configuration using Pydantic Settings
  - `database.py` - SQLite database setup
  - `models/` - SQLModel entities and Pydantic schemas
    - `database.py` - DatabaseConnection model
    - `export.py` - QueryExport model for export history
    - `schemas.py` - Request/Response schemas
  - `services/` - Business logic services
    - `database_service.py` - Database operations
    - `export_service.py` - Export facade service
    - `export_suggestion.py` - AI-powered export suggestions
  - `export/` - Export functionality (Strategy pattern)
    - `base.py` - Abstract base classes and interfaces
    - `csv_exporter.py` - CSV export implementation
    - `json_exporter.py` - JSON export implementation
    - `excel_exporter.py` - Excel export implementation
    - `sql_exporter.py` - SQL INSERT statements export
    - `registry.py` - Export format registry (Factory pattern)
  - `commands/` - Command pattern implementations
    - `export_command.py` - Query and export command
  - `api/v1/` - API route handlers
    - `databases.py` - Database and export endpoints
  - `api_documentation.py` - Comprehensive API documentation
- `tests/` - Test files
  - `unit/` - Unit tests for exporters and services
  - `integration/` - Integration tests for API endpoints
  - `conftest_export.py` - Export test fixtures
- `alembic/` - Database migrations
  - `versions/002_add_export_history.py` - Export history table

## API Endpoints

### Database Management
- `GET /api/v1/dbs` - List database connections
- `POST /api/v1/dbs` - Create database connection
- `GET /api/v1/dbs/{name}` - Get database details
- `DELETE /api/v1/dbs/{name}` - Delete database connection
- `POST /api/v1/dbs/{name}/query` - Execute SQL query

### Export Operations
- `POST /api/v1/dbs/{name}/export` - Export query results
- `POST /api/v1/dbs/{name}/query-and-export` - Query and export in one operation
- `POST /api/v1/dbs/{name}/export/suggest` - Get AI-powered export suggestion
- `POST /api/v1/export/parse-nl` - Parse natural language export command
- `GET /api/v1/dbs/{name}/exports` - Get export history

Full API documentation with examples available at `/docs` (Swagger UI).

## Testing

Run the comprehensive test suite:

```bash
cd backend
chmod +x run_all_tests.sh
./run_all_tests.sh
```

This will run:
- Unit tests (44 test cases for exporters, services, suggestions)
- Integration tests (10 test cases for API endpoints)
- Code coverage report (90% coverage achieved)
- Code quality checks (ruff, mypy)

Test results are saved to `backend/test_results/`.

See [TEST_REPORT.md](../TEST_REPORT.md) for detailed test results and coverage analysis.

## Documentation

- [USER_GUIDE.md](../USER_GUIDE.md) - Comprehensive user guide with scenarios and examples
- [TEST_REPORT.md](../TEST_REPORT.md) - Complete test report with coverage statistics
- [EXPORT_QUICK_START.md](../EXPORT_QUICK_START.md) - Quick start guide for export functionality
- [FULL_IMPLEMENTATION_SUMMARY.md](../FULL_IMPLEMENTATION_SUMMARY.md) - Complete implementation overview
- [backend/EXPORT_IMPLEMENTATION.md](EXPORT_IMPLEMENTATION.md) - Technical implementation details

## Development

- Python 3.12+
- Uses `uv` for package management
- Uses `ruff` for linting
- Uses `mypy` for type checking
- Uses `pytest` for testing

### Architecture Patterns

The export functionality implements several design patterns:
- **Strategy Pattern**: `BaseExporter` with concrete implementations (CSV, JSON, Excel, SQL)
- **Factory Pattern**: `ExportFormatRegistry` for exporter instantiation
- **Facade Pattern**: `ExportService` provides simplified interface
- **Command Pattern**: `ExportCommand` for query + export operations

### Adding New Export Formats

To add a new export format:

1. Create a new exporter class inheriting from `BaseExporter`
2. Implement the `export()` method
3. Register in `app/export/__init__.py`
4. Add corresponding enum value to `ExportFormat`
5. Write unit tests

Example: ~100 lines of code per new format.
