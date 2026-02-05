"""Base classes and data structures for export functionality."""

from abc import ABC, abstractmethod
from typing import Any, BinaryIO, AsyncIterator
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class ExportFormat(str, Enum):
    """Supported export formats."""

    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"
    SQL = "sql"


class ExportOptions(BaseModel):
    """Export options configuration."""

    format: ExportFormat
    delimiter: str = ","  # CSV delimiter
    include_headers: bool = True
    pretty_print: bool = True  # JSON formatting
    sheet_name: str = "Sheet1"  # Excel sheet name
    compress: bool = False  # Whether to compress (.zip)
    max_rows: int | None = None  # Maximum rows limit
    table_name: str = "exported_data"  # SQL table name


class ExportResult(BaseModel):
    """Export result containing file information."""

    file_path: str | None = None  # Server-side export: file path
    file_data: bytes | None = None  # Client-side export: binary data
    file_name: str
    mime_type: str
    row_count: int
    file_size_bytes: int
    export_time_ms: int


class BaseExporter(ABC):
    """Abstract base class for all exporters."""

    @abstractmethod
    async def export(
        self,
        columns: list[dict[str, str]],
        rows: list[dict[str, Any]],
        options: ExportOptions,
    ) -> ExportResult:
        """
        Execute data export.

        Args:
            columns: Column definitions [{"name": "id", "dataType": "integer"}]
            rows: Data rows [{"id": 1, "name": "Alice"}]
            options: Export options

        Returns:
            ExportResult: Export result
        """
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        """Get file extension, e.g., 'csv'."""
        pass

    @abstractmethod
    def get_mime_type(self) -> str:
        """Get MIME type, e.g., 'text/csv'."""
        pass

    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether streaming export is supported (for large datasets)."""
        pass

    @abstractmethod
    async def stream_export(
        self,
        columns: list[dict[str, str]],
        row_iterator: AsyncIterator[dict[str, Any]],
        output: BinaryIO,
        options: ExportOptions,
    ) -> int:
        """
        Stream export for large datasets.

        Returns:
            int: Number of rows exported
        """
        pass

    def validate_options(self, options: ExportOptions) -> tuple[bool, str | None]:
        """
        Validate export options.

        Returns:
            (is_valid, error_message)
        """
        # Default validation
        MAX_EXPORT_ROWS = 1_000_000
        if options.max_rows and options.max_rows > MAX_EXPORT_ROWS:
            return False, f"Cannot export more than {MAX_EXPORT_ROWS} rows"
        return True, None

    def _generate_filename(self, extension: str) -> str:
        """Generate filename with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"export_{timestamp}.{extension}"
