# Database Query Tool

A comprehensive web-based database management tool with advanced query execution and export capabilities.

## Features

- **Multi-Database Support**: Connect to PostgreSQL, MySQL, and SQLite databases
- **Natural Language Queries**: Convert natural language to SQL using AI
- **Advanced Export**: Export query results in CSV, JSON, Excel, and SQL formats
- **Smart Suggestions**: AI-powered export format recommendations
- **Export History**: Complete audit trail of all export operations
- **Real-time Execution**: Execute SQL queries with instant results
- **Metadata Exploration**: Browse database schemas, tables, and columns

## Project Structure

```
db-query/
├── backend/          # FastAPI backend (Python 3.12+)
│   ├── app/          # Application code
│   │   ├── export/   # Export functionality (Strategy pattern)
│   │   ├── services/ # Business logic services
│   │   ├── commands/ # Command pattern implementations
│   │   ├── models/   # SQLModel entities and schemas
│   │   └── api/      # API route handlers
│   ├── tests/        # Unit and integration tests
│   └── alembic/      # Database migrations
├── frontend/         # React frontend (TypeScript, Refine 5)
│   └── src/
│       ├── services/ # API client services
│       └── components/ # React components
├── docs/             # Technical documentation
├── fixtures/         # REST Client test files
├── specs/            # Design specifications
└── Makefile          # Development commands
```

## Quick Start

### Initial Setup

```bash
# Install all dependencies
make install

# Setup database and environment
make setup
# Then edit backend/.env and add your OPENAI_API_KEY

# Run database migrations (important for export functionality)
cd backend
alembic upgrade head
cd ..

# Start development servers
make dev
```

The application will be available at:
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

### Development Commands

```bash
# View all available commands
make help

# Start backend only
make dev-backend

# Start frontend only
make dev-frontend

# Run tests
make test

# Format code
make format

# Run linters
make lint
```

## Quick Export Guide

Export query results in multiple formats with smart AI suggestions:

```bash
# Method 1: Using the UI
# 1. Execute a SQL query in the web interface
# 2. Click export button (CSV, JSON, EXCEL, or SQL)
# 3. Get AI suggestions for optimal format

# Method 2: Using API directly
curl -X POST http://localhost:8000/api/v1/dbs/mydb/query-and-export \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM users LIMIT 100",
    "format": "excel"
  }' \
  --output users.xlsx

# Method 3: Natural language command
curl -X POST http://localhost:8000/api/v1/export/parse-nl \
  -H "Content-Type: application/json" \
  -d '{"command": "导出为 Excel"}'
```

See [USER_GUIDE.md](USER_GUIDE.md) for comprehensive usage instructions.

## API Testing

### Using REST Client (VSCode)

1. Install [REST Client extension](https://marketplace.visualstudio.com/items?itemName=humao.rest-client)
2. Open `fixtures/test.rest`
3. Click "Send Request" above any HTTP request
4. View responses in VSCode panel

See `fixtures/README.md` for detailed testing guide.

### Using Makefile

```bash
# Check if backend is running
make health

# Open API documentation
make docs
```

## Project Status

### ✅ Completed Features

#### Core Infrastructure
- Backend project structure with FastAPI
- Frontend project structure with React + Refine
- Database models and migrations
- Makefile with development tasks
- REST Client test suite

#### Database Management
- Multi-database support (PostgreSQL, MySQL, SQLite)
- Connection management with secure credential storage
- Schema and table metadata exploration
- SQL query execution with syntax validation

#### Export Functionality (Phases 1-7 Complete)
- **4 Export Formats**: CSV, JSON, Excel (.xlsx), SQL (INSERT statements)
- **5 API Endpoints**: Export, query-and-export, suggestions, NL parsing, history
- **Smart Suggestions**: AI-powered format recommendations based on query analysis
- **Natural Language**: Support for Chinese and English export commands
- **Export History**: Complete audit trail with metadata tracking
- **54 Test Cases**: 100% pass rate, 90% code coverage
- **Complete Documentation**: User guide, API docs, test reports

See [FULL_IMPLEMENTATION_SUMMARY.md](FULL_IMPLEMENTATION_SUMMARY.md) for complete implementation details.

### 📊 Statistics

- **Backend**: ~5,800 lines of production code
- **Test Coverage**: 90% (54 test cases, all passing)
- **API Endpoints**: 15+ endpoints
- **Export Formats**: 4 formats with extensible architecture
- **Documentation**: 7 comprehensive guides

## Documentation

- [USER_GUIDE.md](USER_GUIDE.md) - Complete user manual with scenarios
- [TEST_REPORT.md](TEST_REPORT.md) - Test results and coverage analysis
- [EXPORT_QUICK_START.md](EXPORT_QUICK_START.md) - Quick start for export features
- [FULL_IMPLEMENTATION_SUMMARY.md](FULL_IMPLEMENTATION_SUMMARY.md) - Implementation overview
- [docs/README.md](docs/README.md) - Technical documentation
- [backend/EXPORT_IMPLEMENTATION.md](backend/EXPORT_IMPLEMENTATION.md) - Export implementation details

## Architecture

The export functionality follows SOLID principles and implements multiple design patterns:

- **Strategy Pattern**: `BaseExporter` with format-specific implementations
- **Factory Pattern**: `ExportFormatRegistry` for exporter instantiation
- **Facade Pattern**: `ExportService` provides unified interface
- **Command Pattern**: `ExportCommand` for query + export operations

Adding a new export format requires only ~100 lines of code:
1. Create exporter class inheriting from `BaseExporter`
2. Implement `export()` method
3. Register in `ExportFormatRegistry`
4. Write unit tests

## Testing

Run the comprehensive test suite:

```bash
cd backend
chmod +x run_all_tests.sh
./run_all_tests.sh
```

Test results include:
- Unit tests (44 test cases)
- Integration tests (10 test cases)
- Coverage report (90% coverage)
- Code quality checks (ruff, mypy)

Results saved to `backend/test_results/`.
