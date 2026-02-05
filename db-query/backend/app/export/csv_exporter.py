"""CSV exporter implementation."""

import csv
import io
import time
from typing import Any, BinaryIO, AsyncIterator
from app.export.base import BaseExporter, ExportOptions, ExportResult


class CSVExporter(BaseExporter):
    """CSV exporter - RFC 4180 compliant."""

    async def export(
        self,
        columns: list[dict[str, str]],
        rows: list[dict[str, Any]],
        options: ExportOptions,
    ) -> ExportResult:
        """Export data to CSV format."""
        start_time = time.time()
        output = io.StringIO()

        # Extract column names
        column_names = [col["name"] for col in columns]

        # Create CSV writer
        writer = csv.DictWriter(
            output,
            fieldnames=column_names,
            delimiter=options.delimiter,
            quoting=csv.QUOTE_MINIMAL,
        )

        # Write headers
        if options.include_headers:
            writer.writeheader()

        # Write data rows
        for row in rows:
            # Handle None values
            cleaned_row = {k: (v if v is not None else "") for k, v in row.items()}
            writer.writerow(cleaned_row)

        # Get CSV content
        csv_content = output.getvalue()
        file_data = csv_content.encode("utf-8")

        return ExportResult(
            file_data=file_data,
            file_name=self._generate_filename(self.get_file_extension()),
            mime_type=self.get_mime_type(),
            row_count=len(rows),
            file_size_bytes=len(file_data),
            export_time_ms=int((time.time() - start_time) * 1000),
        )

    def get_file_extension(self) -> str:
        """Return 'csv'."""
        return "csv"

    def get_mime_type(self) -> str:
        """Return CSV MIME type."""
        return "text/csv"

    def supports_streaming(self) -> bool:
        """CSV supports streaming."""
        return True

    async def stream_export(
        self,
        columns: list[dict[str, str]],
        row_iterator: AsyncIterator[dict[str, Any]],
        output: BinaryIO,
        options: ExportOptions,
    ) -> int:
        """Stream CSV export for large datasets."""
        column_names = [col["name"] for col in columns]

        # Create text wrapper for binary output
        text_output = io.TextIOWrapper(output, encoding="utf-8", newline="")

        writer = csv.DictWriter(
            text_output, fieldnames=column_names, delimiter=options.delimiter
        )

        # Write headers
        if options.include_headers:
            writer.writeheader()

        # Write rows
        row_count = 0
        async for row in row_iterator:
            cleaned_row = {k: (v if v is not None else "") for k, v in row.items()}
            writer.writerow(cleaned_row)
            row_count += 1

        text_output.flush()
        return row_count
