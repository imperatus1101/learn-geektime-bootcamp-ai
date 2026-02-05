"""Export format registry - Factory pattern."""

from typing import Type
from app.export.base import BaseExporter, ExportFormat


class ExportFormatRegistry:
    """Export format registry - Factory pattern."""

    def __init__(self):
        """Initialize empty registry."""
        self._exporters: dict[ExportFormat, Type[BaseExporter]] = {}

    def register(self, format: ExportFormat, exporter_class: Type[BaseExporter]):
        """
        Register an exporter.

        Args:
            format: Export format enum
            exporter_class: Exporter class type
        """
        self._exporters[format] = exporter_class

    def get_exporter(self, format: ExportFormat) -> BaseExporter:
        """
        Get exporter instance.

        Args:
            format: Export format

        Returns:
            BaseExporter: Exporter instance

        Raises:
            ValueError: If format is not supported
        """
        if format not in self._exporters:
            raise ValueError(f"Unsupported export format: {format}")

        exporter_class = self._exporters[format]
        return exporter_class()

    def list_formats(self) -> list[str]:
        """
        List all supported formats.

        Returns:
            List of format names
        """
        return [fmt.value for fmt in self._exporters.keys()]


# Global registry instance
export_registry = ExportFormatRegistry()

# Register built-in exporters
from app.export.csv_exporter import CSVExporter
from app.export.json_exporter import JSONExporter
from app.export.excel_exporter import ExcelExporter
from app.export.sql_exporter import SQLExporter

export_registry.register(ExportFormat.CSV, CSVExporter)
export_registry.register(ExportFormat.JSON, JSONExporter)
export_registry.register(ExportFormat.EXCEL, ExcelExporter)
export_registry.register(ExportFormat.SQL, SQLExporter)
