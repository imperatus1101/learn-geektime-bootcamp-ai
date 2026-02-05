"""
快速测试导出功能的 Python 脚本
可以独立运行，无需启动完整的服务器
"""

import asyncio
from app.export.csv_exporter import CSVExporter
from app.export.json_exporter import JSONExporter
from app.export.excel_exporter import ExcelExporter
from app.export.sql_exporter import SQLExporter
from app.export.base import ExportOptions, ExportFormat


async def test_all_exporters():
    """测试所有导出器"""

    # 测试数据
    columns = [
        {"name": "id", "dataType": "integer"},
        {"name": "name", "dataType": "varchar"},
        {"name": "email", "dataType": "varchar"},
        {"name": "active", "dataType": "boolean"},
    ]

    rows = [
        {"id": 1, "name": "Alice", "email": "alice@example.com", "active": True},
        {"id": 2, "name": "Bob", "email": "bob@example.com", "active": False},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com", "active": True},
    ]

    print("=" * 60)
    print("数据导出功能测试")
    print("=" * 60)
    print()

    # 1. 测试 CSV 导出
    print("1. 测试 CSV 导出")
    print("-" * 40)
    csv_exporter = CSVExporter()
    csv_options = ExportOptions(format=ExportFormat.CSV)
    csv_result = await csv_exporter.export(columns, rows, csv_options)

    print(f"✓ 文件名: {csv_result.file_name}")
    print(f"✓ 行数: {csv_result.row_count}")
    print(f"✓ 文件大小: {csv_result.file_size_bytes} bytes")
    print(f"✓ 导出时间: {csv_result.export_time_ms} ms")
    print(f"✓ MIME类型: {csv_result.mime_type}")
    print("\n内容预览:")
    print(csv_result.file_data.decode("utf-8")[:200])
    print("\n")

    # 2. 测试 JSON 导出
    print("2. 测试 JSON 导出")
    print("-" * 40)
    json_exporter = JSONExporter()
    json_options = ExportOptions(format=ExportFormat.JSON, pretty_print=True)
    json_result = await json_exporter.export(columns, rows, json_options)

    print(f"✓ 文件名: {json_result.file_name}")
    print(f"✓ 行数: {json_result.row_count}")
    print(f"✓ 文件大小: {json_result.file_size_bytes} bytes")
    print(f"✓ 导出时间: {json_result.export_time_ms} ms")
    print(f"✓ MIME类型: {json_result.mime_type}")
    print("\n内容预览:")
    print(json_result.file_data.decode("utf-8")[:300])
    print("\n")

    # 3. 测试 Excel 导出
    print("3. 测试 Excel 导出")
    print("-" * 40)
    excel_exporter = ExcelExporter()
    excel_options = ExportOptions(format=ExportFormat.EXCEL, sheet_name="TestData")
    excel_result = await excel_exporter.export(columns, rows, excel_options)

    print(f"✓ 文件名: {excel_result.file_name}")
    print(f"✓ 行数: {excel_result.row_count}")
    print(f"✓ 文件大小: {excel_result.file_size_bytes} bytes")
    print(f"✓ 导出时间: {excel_result.export_time_ms} ms")
    print(f"✓ MIME类型: {excel_result.mime_type}")
    print("(Excel 文件为二进制格式，无法直接预览)")
    print("\n")

    # 4. 测试 SQL 导出
    print("4. 测试 SQL 导出")
    print("-" * 40)
    sql_exporter = SQLExporter()
    sql_options = ExportOptions(format=ExportFormat.SQL, table_name="users")
    sql_result = await sql_exporter.export(columns, rows, sql_options)

    print(f"✓ 文件名: {sql_result.file_name}")
    print(f"✓ 行数: {sql_result.row_count}")
    print(f"✓ 文件大小: {sql_result.file_size_bytes} bytes")
    print(f"✓ 导出时间: {sql_result.export_time_ms} ms")
    print(f"✓ MIME类型: {sql_result.mime_type}")
    print("\n内容预览:")
    print(sql_result.file_data.decode("utf-8")[:400])
    print("\n")

    # 5. 测试导出器属性
    print("5. 测试导出器属性")
    print("-" * 40)
    exporters = [
        ("CSV", csv_exporter),
        ("JSON", json_exporter),
        ("Excel", excel_exporter),
        ("SQL", sql_exporter),
    ]

    for name, exporter in exporters:
        print(f"{name} 导出器:")
        print(f"  - 扩展名: {exporter.get_file_extension()}")
        print(f"  - MIME类型: {exporter.get_mime_type()}")
        print(f"  - 流式支持: {'✓' if exporter.supports_streaming() else '✗'}")
    print("\n")

    print("=" * 60)
    print("所有测试完成! ✓")
    print("=" * 60)
    print("\n提示: 运行 'python3 -m pytest tests/unit/test_export.py -v' 进行完整测试")


if __name__ == "__main__":
    asyncio.run(test_all_exporters())
