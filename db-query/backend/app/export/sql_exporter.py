"""SQL exporter implementation."""

import time
from typing import Any, BinaryIO, AsyncIterator
from datetime import datetime
from app.export.base import BaseExporter, ExportOptions, ExportResult


class SQLExporter(BaseExporter):
    """SQL INSERT statements exporter."""

    async def export(
        self,
        columns: list[dict[str, str]],
        rows: list[dict[str, Any]],
        options: ExportOptions,
    ) -> ExportResult:
        """Export data to SQL INSERT statements."""
        start_time = time.time()

        # Generate table name
        table_name = options.table_name
        column_names = [col["name"] for col in columns]

        # Build SQL statements
        sql_statements = []

        # Add comment header
        sql_statements.append(f"-- Exported at {datetime.now().isoformat()}")
        sql_statements.append(f"-- Total rows: {len(rows)}")
        sql_statements.append("")

        # Generate INSERT statements
        for row in rows:
            values = []
            for col_name in column_names:
                value = row.get(col_name)
                if value is None:
                    values.append("NULL")
                elif isinstance(value, str):
                    # Escape single quotes
                    escaped_value = value.replace("'", "''")
                    values.append(f"'{escaped_value}'")
                elif isinstance(value, (int, float)):
                    values.append(str(value))
                elif isinstance(value, bool):
                    # Convert boolean to SQL boolean
                    values.append("TRUE" if value else "FALSE")
                else:
                    # Convert other types to string
                    values.append(f"'{str(value)}'")

            columns_str = ", ".join(column_names)
            values_str = ", ".join(values)
            sql_statements.append(
                f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});"
            )

        sql_content = "\n".join(sql_statements)
        file_data = sql_content.encode("utf-8")

        return ExportResult(
            file_data=file_data,
            file_name=self._generate_filename(self.get_file_extension()),
            mime_type=self.get_mime_type(),
            row_count=len(rows),
            file_size_bytes=len(file_data),
            export_time_ms=int((time.time() - start_time) * 1000),
        )

    def get_file_extension(self) -> str:
        """Return 'sql'."""
        return "sql"

    def get_mime_type(self) -> str:
        """Return SQL MIME type."""
        return "application/sql"

    def supports_streaming(self) -> bool:
        """SQL supports streaming."""
        return True

    async def stream_export(
        self,
        columns: list[dict[str, str]],
        row_iterator: AsyncIterator[dict[str, Any]],
        output: BinaryIO,
        options: ExportOptions,
    ) -> int:
        """Stream SQL export for large datasets."""
        table_name = options.table_name
        column_names = [col["name"] for col in columns]

        # Write header
        header = f"-- Exported at {datetime.now().isoformat()}\n\n"
        output.write(header.encode("utf-8"))

        # Write INSERT statements
        row_count = 0
        async for row in row_iterator:
            values = []
            for col_name in column_names:
                value = row.get(col_name)
                if value is None:
                    values.append("NULL")
                elif isinstance(value, str):
                    escaped_value = value.replace("'", "''")
                    values.append(f"'{escaped_value}'")
                elif isinstance(value, (int, float)):
                    values.append(str(value))
                elif isinstance(value, bool):
                    values.append("TRUE" if value else "FALSE")
                else:
                    values.append(f"'{str(value)}'")

            columns_str = ", ".join(column_names)
            values_str = ", ".join(values)
            sql_line = f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});\n"
            output.write(sql_line.encode("utf-8"))
            row_count += 1

        return row_count
