"""JSON exporter implementation."""

import json
import time
from typing import Any, BinaryIO, AsyncIterator
from datetime import datetime
from app.export.base import BaseExporter, ExportOptions, ExportResult


class JSONExporter(BaseExporter):
    """JSON exporter."""

    async def export(
        self,
        columns: list[dict[str, str]],
        rows: list[dict[str, Any]],
        options: ExportOptions,
    ) -> ExportResult:
        """Export data to JSON format."""
        start_time = time.time()

        # Build export data
        export_data = {
            "columns": columns,
            "rows": rows,
            "metadata": {
                "row_count": len(rows),
                "exported_at": datetime.now().isoformat(),
            },
        }

        # Serialize
        if options.pretty_print:
            json_content = json.dumps(export_data, indent=2, ensure_ascii=False)
        else:
            json_content = json.dumps(export_data, ensure_ascii=False)

        file_data = json_content.encode("utf-8")

        return ExportResult(
            file_data=file_data,
            file_name=self._generate_filename(self.get_file_extension()),
            mime_type=self.get_mime_type(),
            row_count=len(rows),
            file_size_bytes=len(file_data),
            export_time_ms=int((time.time() - start_time) * 1000),
        )

    def get_file_extension(self) -> str:
        """Return 'json'."""
        return "json"

    def get_mime_type(self) -> str:
        """Return JSON MIME type."""
        return "application/json"

    def supports_streaming(self) -> bool:
        """JSON doesn't support streaming (needs complete data structure)."""
        return False

    async def stream_export(
        self,
        columns: list[dict[str, str]],
        row_iterator: AsyncIterator[dict[str, Any]],
        output: BinaryIO,
        options: ExportOptions,
    ) -> int:
        """JSON streaming not supported."""
        raise NotImplementedError("JSON export does not support streaming")
