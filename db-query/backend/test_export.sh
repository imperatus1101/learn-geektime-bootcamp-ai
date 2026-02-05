#!/bin/bash

# 数据导出功能快速测试脚本
# 用于验证 Phase 1-3 的导出功能实现

set -e

echo "================================"
echo "数据导出功能测试脚本"
echo "================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 测试数据
TEST_DB="testdb"
API_BASE="http://localhost:8000/api/v1/dbs"

echo -e "${YELLOW}测试 1: CSV 导出${NC}"
echo "-------------------------------"
curl -X POST "${API_BASE}/${TEST_DB}/export" \
  -H "Content-Type: application/json" \
  -d '{
    "columns": [
      {"name": "id", "dataType": "integer"},
      {"name": "name", "dataType": "varchar"},
      {"name": "email", "dataType": "varchar"}
    ],
    "rows": [
      {"id": 1, "name": "Alice", "email": "alice@example.com"},
      {"id": 2, "name": "Bob", "email": "bob@example.com"},
      {"id": 3, "name": "Charlie", "email": "charlie@example.com"}
    ],
    "format": "csv"
  }' \
  --output test_export.csv \
  -w "\nHTTP Status: %{http_code}\n" 2>/dev/null

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ CSV 导出成功${NC}"
  echo "文件已保存到: test_export.csv"
  echo "文件内容预览:"
  head -n 5 test_export.csv 2>/dev/null || echo "(文件为空或不存在)"
else
  echo -e "${RED}✗ CSV 导出失败${NC}"
fi
echo ""

echo -e "${YELLOW}测试 2: JSON 导出${NC}"
echo "-------------------------------"
curl -X POST "${API_BASE}/${TEST_DB}/export" \
  -H "Content-Type: application/json" \
  -d '{
    "columns": [
      {"name": "id", "dataType": "integer"},
      {"name": "status", "dataType": "varchar"}
    ],
    "rows": [
      {"id": 1, "status": "active"},
      {"id": 2, "status": "inactive"}
    ],
    "format": "json",
    "options": {
      "prettyPrint": true
    }
  }' \
  --output test_export.json \
  -w "\nHTTP Status: %{http_code}\n" 2>/dev/null

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ JSON 导出成功${NC}"
  echo "文件已保存到: test_export.json"
  echo "文件内容预览:"
  head -n 10 test_export.json 2>/dev/null || echo "(文件为空或不存在)"
else
  echo -e "${RED}✗ JSON 导出失败${NC}"
fi
echo ""

echo -e "${YELLOW}测试 3: Excel 导出${NC}"
echo "-------------------------------"
curl -X POST "${API_BASE}/${TEST_DB}/export" \
  -H "Content-Type: application/json" \
  -d '{
    "columns": [
      {"name": "product", "dataType": "varchar"},
      {"name": "price", "dataType": "numeric"},
      {"name": "quantity", "dataType": "integer"}
    ],
    "rows": [
      {"product": "Laptop", "price": 999.99, "quantity": 5},
      {"product": "Mouse", "price": 29.99, "quantity": 50},
      {"product": "Keyboard", "price": 79.99, "quantity": 30}
    ],
    "format": "excel",
    "options": {
      "sheetName": "Products"
    }
  }' \
  --output test_export.xlsx \
  -w "\nHTTP Status: %{http_code}\n" 2>/dev/null

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Excel 导出成功${NC}"
  echo "文件已保存到: test_export.xlsx"
  ls -lh test_export.xlsx 2>/dev/null || echo "(文件不存在)"
else
  echo -e "${RED}✗ Excel 导出失败${NC}"
fi
echo ""

echo -e "${YELLOW}测试 4: SQL 导出${NC}"
echo "-------------------------------"
curl -X POST "${API_BASE}/${TEST_DB}/export" \
  -H "Content-Type: application/json" \
  -d '{
    "columns": [
      {"name": "user_id", "dataType": "integer"},
      {"name": "username", "dataType": "varchar"},
      {"name": "active", "dataType": "boolean"}
    ],
    "rows": [
      {"user_id": 1, "username": "admin", "active": true},
      {"user_id": 2, "username": "user1", "active": false}
    ],
    "format": "sql",
    "options": {
      "tableName": "users"
    }
  }' \
  --output test_export.sql \
  -w "\nHTTP Status: %{http_code}\n" 2>/dev/null

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ SQL 导出成功${NC}"
  echo "文件已保存到: test_export.sql"
  echo "文件内容预览:"
  head -n 10 test_export.sql 2>/dev/null || echo "(文件为空或不存在)"
else
  echo -e "${RED}✗ SQL 导出失败${NC}"
fi
echo ""

echo -e "${YELLOW}测试 5: 查询并导出（一体化）${NC}"
echo "-------------------------------"
curl -X POST "${API_BASE}/${TEST_DB}/query-and-export" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT 1 as id, '\''test'\'' as name",
    "format": "csv"
  }' \
  --output test_query_export.csv \
  -w "\nHTTP Status: %{http_code}\n" 2>/dev/null

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ 查询并导出成功${NC}"
  echo "文件已保存到: test_query_export.csv"
  cat test_query_export.csv 2>/dev/null || echo "(文件为空或不存在)"
else
  echo -e "${RED}✗ 查询并导出失败${NC}"
  echo "注意: 此测试需要已配置的数据库连接"
fi
echo ""

echo "================================"
echo "测试完成！"
echo "================================"
echo ""
echo "生成的文件:"
ls -lh test_export.* test_query_export.* 2>/dev/null || echo "未生成任何文件（可能是因为服务器未运行或数据库连接不存在）"
echo ""
echo "提示:"
echo "1. 确保后端服务正在运行 (uvicorn app.main:app --reload)"
echo "2. 确保已创建测试数据库连接 (名称: ${TEST_DB})"
echo "3. 查看 EXPORT_IMPLEMENTATION.md 了解详细说明"
