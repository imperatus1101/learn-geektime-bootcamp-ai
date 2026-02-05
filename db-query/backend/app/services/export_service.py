"""Export service facade."""

from typing import Any
from sqlmodel import Session, select
from app.export.base import ExportFormat, ExportOptions, ExportResult
from app.export.registry import export_registry
from app.models.export import QueryExport


class ExportService:
    """Export service facade - coordinates export operations."""

    async def export_query_result(
        self,
        columns: list[dict[str, str]],
        rows: list[dict[str, Any]],
        format: ExportFormat,
        options: ExportOptions | None = None,
    ) -> ExportResult:
        """
        Export query result.

        Args:
            columns: Column definitions
            rows: Data rows
            format: Export format
            options: Export options

        Returns:
            ExportResult: Export result

        Raises:
            ValueError: If export options are invalid
        """
        # Use default options if not provided
        if options is None:
            options = ExportOptions(format=format)

        # Get exporter
        exporter = export_registry.get_exporter(format)

        # Validate options
        is_valid, error = exporter.validate_options(options)
        if not is_valid:
            raise ValueError(f"Invalid export options: {error}")

        # Execute export
        result = await exporter.export(columns, rows, options)

        return result

    async def save_export_history(
        self,
        session: Session,
        db_name: str,
        sql: str,
        format: ExportFormat,
        result: ExportResult,
    ) -> QueryExport:
        """
        Save export history to database.

        Args:
            session: Database session
            db_name: Database name
            sql: SQL query
            format: Export format
            result: Export result

        Returns:
            QueryExport: Created export history record
        """
        export_record = QueryExport(
            database_name=db_name,
            sql=sql,
            export_format=format.value,
            file_name=result.file_name,
            file_path=result.file_path,
            file_size_bytes=result.file_size_bytes,
            row_count=result.row_count,
            export_time_ms=result.export_time_ms,
        )

        session.add(export_record)
        session.commit()
        session.refresh(export_record)

        return export_record

    async def get_export_history(
        self, session: Session, db_name: str, limit: int = 10
    ) -> list[QueryExport]:
        """
        Get export history.

        Args:
            session: Database session
            db_name: Database name
            limit: Maximum number of records

        Returns:
            List of export history records
        """
        statement = (
            select(QueryExport)
            .where(QueryExport.database_name == db_name)
            .order_by(QueryExport.created_at.desc())
            .limit(limit)
        )

        results = session.exec(statement).all()
        return list(results)


# Global service instance
export_service = ExportService()
