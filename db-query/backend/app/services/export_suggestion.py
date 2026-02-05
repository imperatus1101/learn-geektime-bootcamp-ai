"""Export suggestion service - AI-driven export recommendations."""

from typing import Any
from pydantic import BaseModel
from app.export.base import ExportFormat


class ExportSuggestion(BaseModel):
    """Export suggestion result."""

    should_suggest: bool  # Whether to suggest export
    suggested_format: ExportFormat  # Recommended export format
    reason: str  # Reason for suggestion
    prompt_text: str  # Text to show to user


class ExportSuggestionService:
    """
    Export suggestion service - analyzes query results and provides recommendations.

    Use cases:
    1. After query completion, AI analyzes results and suggests export
    2. Parse user's natural language commands ("export as CSV")
    3. Recommend best export format based on data characteristics
    """

    async def analyze_query_result(
        self,
        sql: str,
        row_count: int,
        columns: list[dict[str, str]],
    ) -> ExportSuggestion:
        """
        Analyze query result and determine if export should be suggested.

        Rules:
        - More than 100 rows: suggest export
        - Contains aggregation functions (SUM, AVG, COUNT): suggest Excel (for analysis)
        - Simple SELECT: suggest CSV
        - Complex nested queries: suggest JSON

        Args:
            sql: SQL query
            row_count: Number of rows returned
            columns: Column definitions

        Returns:
            ExportSuggestion: Suggestion result
        """
        should_suggest = False
        suggested_format = ExportFormat.CSV
        reason = ""

        # Rule 1: Row count check
        if row_count >= 100:
            should_suggest = True
            reason = f"查询返回了 {row_count} 行数据，建议导出以便进一步分析"

        # Rule 2: SQL analysis
        sql_upper = sql.upper()
        if any(agg in sql_upper for agg in ["SUM(", "AVG(", "COUNT(", "GROUP BY"]):
            suggested_format = ExportFormat.EXCEL
            if reason:
                reason += "。检测到聚合函数，Excel 格式更适合数据分析"
            else:
                reason = "检测到聚合函数，Excel 格式更适合数据分析"
                should_suggest = True
        elif "JOIN" in sql_upper or sql_upper.count("SELECT") > 1:
            suggested_format = ExportFormat.JSON
            if reason:
                reason += "。检测到复杂查询，JSON 格式保留数据结构"
            else:
                reason = "检测到复杂查询，JSON 格式保留数据结构"
                should_suggest = True

        # Rule 3: Column count check
        if len(columns) > 10:
            should_suggest = True
            suggested_format = ExportFormat.EXCEL
            if reason:
                reason += f"。查询包含 {len(columns)} 列，Excel 便于查看"
            else:
                reason = f"查询包含 {len(columns)} 列，Excel 便于查看"

        # Generate prompt text
        if should_suggest:
            format_name = {
                ExportFormat.CSV: "CSV",
                ExportFormat.JSON: "JSON",
                ExportFormat.EXCEL: "Excel",
                ExportFormat.SQL: "SQL",
            }[suggested_format]

            prompt_text = f"需要将这次的查询结果导出为 {format_name} 文件吗？{reason}"
        else:
            prompt_text = ""

        return ExportSuggestion(
            should_suggest=should_suggest,
            suggested_format=suggested_format,
            reason=reason,
            prompt_text=prompt_text,
        )

    async def parse_nl_export_command(self, user_input: str) -> dict[str, Any] | None:
        """
        Parse natural language export command.

        Example inputs:
        - "导出为 CSV"
        - "把这个结果保存成 Excel"
        - "导出上次查询的结果为 JSON"

        Args:
            user_input: User's natural language input

        Returns:
            Command dict with action, format, target or None if not an export command

        Note:
            This is a simplified implementation. For production, consider using
            OpenAI or other LLM for better natural language understanding.
        """
        # Simple pattern matching implementation
        user_input_lower = user_input.lower()

        # Check if it's an export command
        export_keywords = ["导出", "保存", "下载", "export", "save", "download"]
        if not any(keyword in user_input_lower for keyword in export_keywords):
            return None

        # Determine format
        format_map = {
            "csv": ExportFormat.CSV,
            "json": ExportFormat.JSON,
            "excel": ExportFormat.EXCEL,
            "xlsx": ExportFormat.EXCEL,
            "sql": ExportFormat.SQL,
        }

        detected_format = None
        for keyword, export_format in format_map.items():
            if keyword in user_input_lower:
                detected_format = export_format
                break

        # Default to CSV if no format specified
        if detected_format is None:
            detected_format = ExportFormat.CSV

        # Determine target (current or last query)
        target = "current"
        if any(word in user_input_lower for word in ["上次", "上一次", "last", "previous"]):
            target = "last"

        return {
            "action": "export",
            "format": detected_format.value,
            "target": target,
        }


# Global service instance
export_suggestion_service = ExportSuggestionService()
