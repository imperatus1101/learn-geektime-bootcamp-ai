"""Export command - implements query + export automation."""

from enum import Enum
from typing import Any
from sqlmodel import Session
from app.models.database import DatabaseType
from app.export.base import ExportFormat, ExportOptions, ExportResult
from app.services.database_service import DatabaseService
from app.services.export_service import ExportService


class CommandStatus(str, Enum):
    """Command execution status."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportCommand:
    """
    Export command - implements query + export in one operation.

    Use cases:
    1. Automation scripts: scheduled query and export
    2. API calls: one request to complete query and export
    3. CLI tools: one-command export

    Example:
        command = ExportCommand(database_service, export_service)
        result = await command.execute(
            db_type=DatabaseType.POSTGRESQL,
            db_name="mydb",
            db_url="postgresql://...",
            sql="SELECT * FROM users",
            export_format=ExportFormat.CSV
        )
    """

    def __init__(
        self, db_service: DatabaseService, export_service: ExportService
    ):
        """Initialize command with required services."""
        self.db_service = db_service
        self.export_service = export_service
        self.status = CommandStatus.PENDING
        self.error: str | None = None
        self.result: ExportResult | None = None

    async def execute(
        self,
        db_type: DatabaseType,
        db_name: str,
        db_url: str,
        sql: str,
        export_format: ExportFormat,
        export_options: ExportOptions | None = None,
        session: Session | None = None,
    ) -> ExportResult:
        """
        Execute query and export in one operation.

        Args:
            db_type: Database type
            db_name: Database name
            db_url: Connection URL
            sql: SQL query
            export_format: Export format
            export_options: Export options (optional)
            session: Database session for history (optional)

        Returns:
            ExportResult: Export result

        Raises:
            Exception: If query or export fails
        """
        self.status = CommandStatus.EXECUTING

        try:
            # Step 1: Execute query
            query_result, execution_time_ms = await self.db_service.execute_query(
                db_type=db_type, name=db_name, url=db_url, sql=sql
            )

            # Convert query result to export format
            columns = [
                {"name": col.name, "dataType": col.data_type}
                for col in query_result.columns
            ]
            rows = query_result.rows

            # Step 2: Export result
            if export_options is None:
                export_options = ExportOptions(format=export_format)

            export_result = await self.export_service.export_query_result(
                columns=columns,
                rows=rows,
                format=export_format,
                options=export_options,
            )

            # Step 3: Save history (if session provided)
            if session is not None:
                await self.export_service.save_export_history(
                    session=session,
                    db_name=db_name,
                    sql=sql,
                    format=export_format,
                    result=export_result,
                )

            self.status = CommandStatus.COMPLETED
            self.result = export_result
            return export_result

        except Exception as e:
            self.status = CommandStatus.FAILED
            self.error = str(e)
            raise

    async def undo(self) -> None:
        """
        Undo operation (delete exported file if exists).

        Note: Currently not implemented as files are sent directly to client.
        """
        # TODO: Implement if we add server-side file storage
        pass

    def get_status(self) -> CommandStatus:
        """Get command execution status."""
        return self.status
