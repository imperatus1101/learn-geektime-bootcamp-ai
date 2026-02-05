"""Database connection management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlmodel import Session, select
from typing import List
from app.database import get_session
from app.models.database import DatabaseConnection, ConnectionStatus, DatabaseType
from app.utils.db_parser import detect_database_type
from app.models.schemas import (
    DatabaseConnectionInput,
    DatabaseConnectionResponse,
    DatabaseMetadataResponse,
    TableMetadata,
    ExportRequest,
    QueryAndExportRequest,
    ExportSuggestionRequest,
    ExportSuggestionResponse,
    NLCommandRequest,
    QueryExportEntry,
)
from app.services.database_service import database_service
from app.services.metadata import fetch_metadata
from app.services.export_service import export_service
from app.services.export_suggestion import export_suggestion_service
from app.commands.export_command import ExportCommand
from app.export.base import ExportFormat, ExportOptions as BaseExportOptions
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1/dbs", tags=["databases"])


def to_response(conn: DatabaseConnection) -> DatabaseConnectionResponse:
    """Convert DatabaseConnection to response schema."""
    return DatabaseConnectionResponse(
        name=conn.name,
        url=conn.url,
        db_type=conn.db_type.value,
        description=conn.description,
        created_at=conn.created_at,
        updated_at=conn.updated_at,
        last_connected_at=conn.last_connected_at,
        status=conn.status.value,
    )


@router.put("/{name}", response_model=DatabaseConnectionResponse)
async def create_or_update_database(
    name: str,
    input_data: DatabaseConnectionInput,
    session: Session = Depends(get_session),
) -> DatabaseConnectionResponse:
    """
    Create or update a database connection.

    Args:
        name: Database connection name
        input_data: Connection input data
        session: Database session

    Returns:
        Created/updated database connection
    """
    # Validate name format
    if not name.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name must contain only alphanumeric characters, hyphens, and underscores",
        )

    # Detect or validate database type
    try:
        if input_data.db_type:
            # Validate provided db_type
            db_type = DatabaseType(input_data.db_type.lower())
            # Also verify it matches URL
            detected_type = detect_database_type(input_data.url)
            if db_type != detected_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Database type mismatch: provided '{db_type.value}' but URL indicates '{detected_type.value}'",
                )
        else:
            # Auto-detect from URL
            db_type = detect_database_type(input_data.url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Test connection
    success, error_message = await database_service.test_connection(db_type, input_data.url)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection test failed: {error_message}",
        )

    # Check if connection exists
    statement = select(DatabaseConnection).where(
        DatabaseConnection.name == name
    )
    existing = session.exec(statement).first()

    if existing:
        # Update existing connection
        existing.url = input_data.url
        existing.db_type = db_type
        existing.description = input_data.description
        existing.updated_at = datetime.now(timezone.utc)
        existing.last_connected_at = datetime.now(timezone.utc)
        existing.status = ConnectionStatus.ACTIVE
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return to_response(existing)
    else:
        # Create new connection
        new_conn = DatabaseConnection(
            name=name,
            url=input_data.url,
            db_type=db_type,
            description=input_data.description,
            status=ConnectionStatus.ACTIVE,
            last_connected_at=datetime.now(timezone.utc),
        )
        session.add(new_conn)
        session.commit()
        session.refresh(new_conn)
        return to_response(new_conn)


@router.get("", response_model=List[DatabaseConnectionResponse])
async def list_databases(
    session: Session = Depends(get_session),
) -> List[DatabaseConnectionResponse]:
    """
    List all database connections.

    Args:
        session: Database session

    Returns:
        List of database connections
    """
    statement = select(DatabaseConnection)
    connections = session.exec(statement).all()
    return [to_response(conn) for conn in connections]


@router.get("/{name}", response_model=DatabaseMetadataResponse)
async def get_database_metadata(
    name: str,
    refresh: bool = False,
    session: Session = Depends(get_session),
) -> DatabaseMetadataResponse:
    """
    Get database metadata (tables, views, columns).

    Args:
        name: Database connection name
        refresh: Force refresh metadata
        session: Database session

    Returns:
        Database metadata
    """
    # Get connection
    statement = select(DatabaseConnection).where(
        DatabaseConnection.name == name
    )
    connection = session.exec(statement).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection '{name}' not found",
        )

    # Fetch metadata
    metadata_dict = await fetch_metadata(
        session, name, connection.db_type, connection.url, force_refresh=refresh
    )

    # Parse metadata
    tables = [
        TableMetadata(**table) for table in metadata_dict.get("tables", [])
    ]
    views = [
        TableMetadata(**view) for view in metadata_dict.get("views", [])
    ]

    # Get cache info
    from app.services.metadata import get_cached_metadata

    cached = await get_cached_metadata(session, name)
    fetched_at = cached.fetched_at if cached else datetime.now(timezone.utc)
    is_stale = cached.is_stale if cached else False

    return DatabaseMetadataResponse(
        databaseName=name,
        tables=tables,
        views=views,
        fetchedAt=fetched_at,
        isStale=is_stale,
    )


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_database(
    name: str,
    session: Session = Depends(get_session),
) -> None:
    """
    Delete a database connection.

    Args:
        name: Database connection name
        session: Database session
    """
    # Get connection
    statement = select(DatabaseConnection).where(
        DatabaseConnection.name == name
    )
    connection = session.exec(statement).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection '{name}' not found",
        )

    # Close connection pool
    await database_service.close_connection(connection.db_type, name)

    # Delete connection
    session.delete(connection)
    session.commit()


@router.post("/{name}/refresh", response_model=DatabaseMetadataResponse)
async def refresh_database_metadata(
    name: str,
    session: Session = Depends(get_session),
) -> DatabaseMetadataResponse:
    """
    Refresh database metadata cache.

    Args:
        name: Database connection name
        session: Database session

    Returns:
        Refreshed database metadata
    """
    # Get connection
    statement = select(DatabaseConnection).where(
        DatabaseConnection.name == name
    )
    connection = session.exec(statement).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection '{name}' not found",
        )

    # Force refresh metadata
    metadata_dict = await fetch_metadata(
        session, name, connection.db_type, connection.url, force_refresh=True
    )

    # Parse metadata
    tables = [
        TableMetadata(**table) for table in metadata_dict.get("tables", [])
    ]
    views = [
        TableMetadata(**view) for view in metadata_dict.get("views", [])
    ]

    # Get cache info
    from app.services.metadata import get_cached_metadata

    cached = await get_cached_metadata(session, name)
    fetched_at = cached.fetched_at if cached else datetime.now(timezone.utc)
    is_stale = False  # Just refreshed

    return DatabaseMetadataResponse(
        databaseName=name,
        tables=tables,
        views=views,
        fetchedAt=fetched_at,
        isStale=is_stale,
    )


@router.post("/{name}/export")
async def export_query_result(
    name: str,
    request: ExportRequest,
    session: Session = Depends(get_session),
) -> Response:
    """
    Export query result to specified format.

    Args:
        name: Database connection name
        request: Export request with columns, rows, format, and options
        session: Database session

    Returns:
        File download response

    Supported formats:
        - csv: Comma-separated values
        - json: JSON format with metadata
        - excel: Excel spreadsheet (.xlsx)
        - sql: SQL INSERT statements
    """
    # Verify database connection exists
    statement = select(DatabaseConnection).where(DatabaseConnection.name == name)
    connection = session.exec(statement).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection '{name}' not found",
        )

    try:
        # Convert request format to ExportFormat enum
        export_format = ExportFormat(request.format)

        # Convert request options to BaseExportOptions if provided
        export_options = None
        if request.options:
            export_options = BaseExportOptions(
                format=export_format,
                delimiter=request.options.delimiter,
                include_headers=request.options.include_headers,
                pretty_print=request.options.pretty_print,
                sheet_name=request.options.sheet_name,
                table_name=request.options.table_name,
            )

        # Convert QueryColumn to dict format
        columns = [{"name": col.name, "dataType": col.data_type} for col in request.columns]

        # Execute export
        result = await export_service.export_query_result(
            columns=columns,
            rows=request.rows,
            format=export_format,
            options=export_options,
        )

        # Return file as download
        return Response(
            content=result.file_data,
            media_type=result.mime_type,
            headers={"Content-Disposition": f'attachment; filename="{result.file_name}"'},
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )


@router.post("/{name}/query-and-export")
async def query_and_export(
    name: str,
    request: QueryAndExportRequest,
    session: Session = Depends(get_session),
) -> Response:
    """
    Execute SQL query and export results in one operation.

    Args:
        name: Database connection name
        request: Query and export request
        session: Database session

    Returns:
        File download response

    This endpoint combines query execution and export in a single operation,
    useful for automation scripts and batch operations.
    """
    # Get database connection
    statement = select(DatabaseConnection).where(DatabaseConnection.name == name)
    connection = session.exec(statement).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection '{name}' not found",
        )

    try:
        # Convert request format to ExportFormat enum
        export_format = ExportFormat(request.format)

        # Convert request options if provided
        export_options = None
        if request.options:
            export_options = BaseExportOptions(
                format=export_format,
                delimiter=request.options.delimiter,
                include_headers=request.options.include_headers,
                pretty_print=request.options.pretty_print,
                sheet_name=request.options.sheet_name,
                table_name=request.options.table_name,
            )

        # Create and execute command
        command = ExportCommand(database_service, export_service)
        result = await command.execute(
            db_type=connection.db_type,
            db_name=name,
            db_url=connection.url,
            sql=request.sql,
            export_format=export_format,
            export_options=export_options,
            session=session,  # Pass session to save history
        )

        # Return file as download
        return Response(
            content=result.file_data,
            media_type=result.mime_type,
            headers={"Content-Disposition": f'attachment; filename="{result.file_name}"'},
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query and export failed: {str(e)}",
        )


@router.post("/{name}/export/suggest", response_model=ExportSuggestionResponse)
async def suggest_export(
    name: str,
    request: ExportSuggestionRequest,
    session: Session = Depends(get_session),
) -> ExportSuggestionResponse:
    """
    Analyze query result and provide export suggestion.

    Args:
        name: Database connection name
        request: Query result information
        session: Database session

    Returns:
        Export suggestion with recommended format and reason

    This endpoint uses rule-based AI to analyze query characteristics
    and suggest the most appropriate export format.
    """
    # Verify database connection exists
    statement = select(DatabaseConnection).where(DatabaseConnection.name == name)
    connection = session.exec(statement).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection '{name}' not found",
        )

    try:
        # Convert QueryColumn to dict format
        columns = [{"name": col.name, "dataType": col.data_type} for col in request.columns]

        # Get suggestion
        suggestion = await export_suggestion_service.analyze_query_result(
            sql=request.sql,
            row_count=request.row_count,
            columns=columns,
        )

        return ExportSuggestionResponse(
            should_suggest=suggestion.should_suggest,
            suggested_format=suggestion.suggested_format.value,
            reason=suggestion.reason,
            prompt_text=suggestion.prompt_text,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate export suggestion: {str(e)}",
        )


@router.post("/export/parse-nl")
async def parse_nl_export_command(request: NLCommandRequest) -> dict:
    """
    Parse natural language export command.

    Args:
        request: Natural language input

    Returns:
        Parsed command dict or {"action": None} if not an export command

    Example inputs:
    - "导出为 CSV"
    - "把这个结果保存成 Excel"
    - "export as JSON"
    """
    try:
        result = await export_suggestion_service.parse_nl_export_command(request.input)

        if result is None:
            return {"action": None}

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse command: {str(e)}",
        )


@router.get("/{name}/exports", response_model=List[QueryExportEntry])
async def get_export_history(
    name: str,
    limit: int = 10,
    session: Session = Depends(get_session),
) -> List[QueryExportEntry]:
    """
    Get export history for a database.

    Args:
        name: Database connection name
        limit: Maximum number of records to return (default: 10)
        session: Database session

    Returns:
        List of export history entries

    This endpoint retrieves the export history for auditing and
    tracking purposes.
    """
    # Verify database connection exists
    statement = select(DatabaseConnection).where(DatabaseConnection.name == name)
    connection = session.exec(statement).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection '{name}' not found",
        )

    try:
        # Get export history
        history = await export_service.get_export_history(session, name, limit)

        # Convert to response schema
        return [
            QueryExportEntry(
                id=entry.id,
                database_name=entry.database_name,
                sql=entry.sql,
                export_format=entry.export_format,
                file_name=entry.file_name,
                file_size_bytes=entry.file_size_bytes,
                row_count=entry.row_count,
                export_time_ms=entry.export_time_ms,
                created_at=entry.created_at,
            )
            for entry in history
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve export history: {str(e)}",
        )
