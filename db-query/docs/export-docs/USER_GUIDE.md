# 数据导出功能 - 用户指南

## 目录

1. [功能概述](#功能概述)
2. [快速开始](#快速开始)
3. [导出格式详解](#导出格式详解)
4. [使用场景](#使用场景)
5. [高级功能](#高级功能)
6. [常见问题](#常见问题)
7. [最佳实践](#最佳实践)
8. [故障排除](#故障排除)

## 功能概述

数据导出功能允许您将查询结果导出为多种格式，方便数据分析、共享和备份。

### 核心特性

✅ **多格式支持**: CSV、JSON、Excel、SQL 四种格式
✅ **智能建议**: AI 自动推荐最佳导出格式
✅ **一键导出**: 查询和导出一步完成
✅ **历史记录**: 完整的导出审计追踪
✅ **大数据支持**: 自动优化处理大型数据集
✅ **灵活配置**: 自定义分隔符、表头等选项

## 快速开始

### 1. 基本导出流程

1. **执行 SQL 查询**
   ```sql
   SELECT * FROM users LIMIT 100
   ```

2. **选择导出格式**
   - 点击 `CSV` 按钮 - 通用表格格式
   - 点击 `JSON` 按钮 - 程序可读格式
   - 点击 `EXCEL` 按钮 - Excel 工作表
   - 点击 `SQL` 按钮 - INSERT 语句

3. **下载文件**
   - 浏览器自动下载
   - 文件名带时间戳，如 `mydb_20260205_120530.csv`

### 2. 使用智能建议

当查询返回大量数据（≥50 行）时，系统会自动显示导出建议：

1. **自动弹窗**
   - 显示推荐的导出格式
   - 说明推荐原因
   - 可选择其他格式

2. **手动触发**
   - 点击 `EXPORT` 按钮
   - 查看建议并选择格式
   - 确认导出

### 3. 查看导出历史

通过 API 查询历史记录：

```bash
curl http://localhost:8000/api/v1/dbs/mydb/exports?limit=10
```

## 导出格式详解

### CSV (Comma-Separated Values)

**适用场景**:
- 通用数据交换
- Excel 导入
- 数据分析工具
- 简单数据备份

**优点**:
- ✅ 文件小巧
- ✅ 兼容性最好
- ✅ 易于编辑
- ✅ 快速导出

**缺点**:
- ❌ 不保留数据类型
- ❌ 特殊字符需转义
- ❌ 不支持多工作表

**示例输出**:
```csv
id,name,email,created_at
1,Alice,alice@example.com,2026-01-01
2,Bob,bob@example.com,2026-01-02
```

**自定义选项**:
```json
{
  "delimiter": ";",        // 分隔符（默认逗号）
  "includeHeaders": true   // 是否包含表头
}
```

### JSON (JavaScript Object Notation)

**适用场景**:
- API 数据交换
- 程序处理
- 保留数据结构
- 配置文件

**优点**:
- ✅ 保留数据类型
- ✅ 支持嵌套结构
- ✅ 易于程序解析
- ✅ 可读性好

**缺点**:
- ❌ 文件较大
- ❌ 不适合 Excel 打开
- ❌ 不适合大数据集

**示例输出**:
```json
{
  "columns": [
    {"name": "id", "dataType": "integer"},
    {"name": "name", "dataType": "varchar"}
  ],
  "rows": [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"}
  ],
  "metadata": {
    "row_count": 2,
    "exported_at": "2026-02-05T12:00:00"
  }
}
```

**自定义选项**:
```json
{
  "prettyPrint": true  // 格式化输出（默认 true）
}
```

### Excel (.xlsx)

**适用场景**:
- 数据分析
- 报表生成
- 业务人员使用
- 多列复杂数据

**优点**:
- ✅ 格式化表格
- ✅ 自动列宽
- ✅ 表头加粗
- ✅ Excel 原生支持

**缺点**:
- ❌ 文件较大
- ❌ 需要 Excel/LibreOffice 打开
- ❌ 不易程序化处理

**特性**:
- 自动调整列宽
- 表头粗体显示
- 支持大数据集（流式写入）
- 可自定义工作表名称

**自定义选项**:
```json
{
  "sheetName": "Users Report"  // 工作表名称
}
```

### SQL (INSERT Statements)

**适用场景**:
- 数据库迁移
- 数据备份
- 跨库导入
- 测试数据生成

**优点**:
- ✅ 直接可执行
- ✅ 保留数据类型
- ✅ 易于版本控制
- ✅ 适合批量导入

**缺点**:
- ❌ 文件最大
- ❌ 不适合大数据集
- ❌ 需要数据库执行

**示例输出**:
```sql
-- Exported at 2026-02-05T12:00:00
-- Total rows: 2

INSERT INTO users (id, name, email) VALUES (1, 'Alice', 'alice@example.com');
INSERT INTO users (id, name, email) VALUES (2, 'Bob', 'bob@example.com');
```

**自定义选项**:
```json
{
  "tableName": "users"  // 目标表名
}
```

## 使用场景

### 场景 1: 日常数据导出

**需求**: 导出用户列表用于 Excel 分析

**步骤**:
1. 查询: `SELECT * FROM users WHERE active = true`
2. 点击 `EXCEL` 按钮
3. 下载 Excel 文件
4. 在 Excel 中打开分析

**推荐格式**: Excel（便于分析和可视化）

### 场景 2: API 数据交换

**需求**: 导出数据供其他系统使用

**步骤**:
1. 使用 API 查询并导出
   ```bash
   curl -X POST http://localhost:8000/api/v1/dbs/mydb/query-and-export \
     -H "Content-Type: application/json" \
     -d '{"sql": "SELECT * FROM products", "format": "json"}' \
     --output products.json
   ```

**推荐格式**: JSON（保留数据类型和结构）

### 场景 3: 数据库迁移

**需求**: 从生产库导出数据到测试库

**步骤**:
1. 导出为 SQL: `SELECT * FROM orders WHERE date >= '2026-01-01'`
2. 点击 `SQL` 按钮
3. 在目标数据库执行 SQL 文件

**推荐格式**: SQL（直接可执行）

### 场景 4: 定时报表

**需求**: 每日自动导出销售数据

**方法**: 使用 cron + API

```bash
# crontab 配置
0 9 * * * curl -X POST http://localhost:8000/api/v1/dbs/mydb/query-and-export \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM sales WHERE date = CURRENT_DATE", "format": "excel"}' \
  --output /reports/sales_$(date +\%Y\%m\%d).xlsx
```

**推荐格式**: Excel（业务人员友好）

### 场景 5: 大数据集导出

**需求**: 导出 10 万行数据

**特点**:
- 系统自动使用服务端导出
- 支持流式处理
- 不会卡死浏览器

**推荐格式**: CSV（性能最好）

## 高级功能

### 1. 智能建议系统

系统根据查询特征自动推荐格式：

#### 聚合查询 → Excel
```sql
SELECT category, SUM(amount), AVG(price)
FROM sales
GROUP BY category
```
**推荐**: Excel（适合进一步分析）

#### 复杂查询 → JSON
```sql
SELECT u.*, o.order_date
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.created_at > '2026-01-01'
```
**推荐**: JSON（保留数据结构）

#### 简单查询 → CSV
```sql
SELECT id, name, email FROM users LIMIT 100
```
**推荐**: CSV（通用、轻量）

### 2. 自定义导出选项

#### CSV 自定义分隔符

**用例**: 导出分号分隔的 CSV（欧洲标准）

```bash
curl -X POST http://localhost:8000/api/v1/dbs/mydb/export \
  -H "Content-Type: application/json" \
  -d '{
    "columns": [...],
    "rows": [...],
    "format": "csv",
    "options": {
      "delimiter": ";"
    }
  }'
```

#### Excel 自定义工作表名

**用例**: 创建有意义的工作表名称

```bash
curl -X POST http://localhost:8000/api/v1/dbs/mydb/export \
  -H "Content-Type: application/json" \
  -d '{
    "columns": [...],
    "rows": [...],
    "format": "excel",
    "options": {
      "sheetName": "2026年1月销售数据"
    }
  }'
```

### 3. 导出历史审计

查询导出历史：

```bash
# 获取最近 10 次导出
curl http://localhost:8000/api/v1/dbs/mydb/exports?limit=10

# 响应示例
[
  {
    "id": 1,
    "databaseName": "mydb",
    "sql": "SELECT * FROM users WHERE active = true",
    "exportFormat": "excel",
    "fileName": "export_20260205_120000.xlsx",
    "fileSizeBytes": 51200,
    "rowCount": 1500,
    "exportTimeMs": 450,
    "createdAt": "2026-02-05T12:00:00"
  }
]
```

**用途**:
- 审计合规
- 性能分析
- 使用统计
- 问题追踪

## 常见问题

### Q1: 为什么导出的 CSV 在 Excel 中乱码？

**A**: Excel 默认使用系统编码打开 CSV。解决方案：

1. **方法 1**: 使用 Excel 导入功能
   - 打开 Excel
   - 数据 → 从文本/CSV
   - 选择 UTF-8 编码

2. **方法 2**: 导出为 Excel 格式
   - 直接点击 `EXCEL` 按钮
   - 无编码问题

### Q2: 导出大数据集时浏览器卡死？

**A**: 系统会自动处理：

- **小数据集** (<10k 行): 客户端导出（更快）
- **大数据集** (≥10k 行): 服务端导出（不卡顿）

您无需做任何设置，系统自动优化。

### Q3: 如何导出包含特殊字符的数据？

**A**: 所有格式都正确处理特殊字符：

- **CSV**: 自动转义引号和换行
- **JSON**: 原生支持 Unicode
- **Excel**: 完全支持
- **SQL**: 自动转义单引号

示例：
```
输入: John "Doe", O'Brien
CSV: "John ""Doe""", 'O''Brien'
```

### Q4: 能否自定义文件名？

**A**: 当前自动生成时间戳文件名：
- 格式: `{database}_{timestamp}.{ext}`
- 示例: `mydb_20260205_120530.csv`

如需自定义，下载后手动重命名即可。

### Q5: 导出的 SQL 文件如何使用？

**A**: 直接在目标数据库执行：

```bash
# PostgreSQL
psql -U username -d database -f export.sql

# MySQL
mysql -u username -p database < export.sql

# SQLite
sqlite3 database.db < export.sql
```

### Q6: 支持导出到云存储吗？

**A**: 当前版本不支持，但可以通过脚本实现：

```bash
# 导出并上传到 S3
curl ... --output temp.csv && \
aws s3 cp temp.csv s3://bucket/path/ && \
rm temp.csv
```

### Q7: 最大能导出多少行？

**A**: 理论上限：
- **CSV**: 1,000,000 行（默认限制）
- **JSON**: 100,000 行（性能考虑）
- **Excel**: 1,048,576 行（Excel 限制）
- **SQL**: 100,000 行（文件大小考虑）

建议：超过 10 万行使用 CSV 格式。

## 最佳实践

### 1. 选择合适的格式

| 数据量 | 用途 | 推荐格式 |
|--------|------|---------|
| <1k 行 | 快速查看 | CSV |
| 1k-10k | 数据分析 | Excel |
| 10k-100k | 大数据导出 | CSV |
| >100k | 程序处理 | CSV (流式) |
| 复杂结构 | API 交换 | JSON |
| 数据迁移 | 跨库导入 | SQL |

### 2. 优化导出性能

**小技巧**:

1. **使用 LIMIT 限制行数**
   ```sql
   SELECT * FROM large_table LIMIT 10000
   ```

2. **只选择需要的列**
   ```sql
   SELECT id, name, email FROM users  -- 好
   SELECT * FROM users  -- 避免
   ```

3. **添加索引优化查询**
   ```sql
   CREATE INDEX idx_created_at ON orders(created_at)
   SELECT * FROM orders WHERE created_at > '2026-01-01'
   ```

### 3. 数据安全

**注意事项**:

1. ✅ 导出前检查敏感信息
2. ✅ 使用 WHERE 子句过滤数据
3. ✅ 避免导出密码等敏感字段
4. ✅ 定期清理导出文件

**示例**:
```sql
-- 好的做法
SELECT id, username, email FROM users

-- 避免
SELECT * FROM users  -- 可能包含 password_hash
```

### 4. 自动化导出

**使用场景**: 定时报表、数据备份

**Shell 脚本示例**:
```bash
#!/bin/bash
# daily_export.sh

DATE=$(date +%Y%m%d)
OUTPUT_DIR="/backups/${DATE}"
mkdir -p "${OUTPUT_DIR}"

# 导出多个表
for table in users orders products; do
  curl -X POST http://localhost:8000/api/v1/dbs/mydb/query-and-export \
    -H "Content-Type: application/json" \
    -d "{\"sql\": \"SELECT * FROM ${table}\", \"format\": \"csv\"}" \
    --output "${OUTPUT_DIR}/${table}.csv"
done

echo "Export completed: ${OUTPUT_DIR}"
```

**Cron 配置**:
```bash
# 每天凌晨 2 点执行
0 2 * * * /path/to/daily_export.sh >> /var/log/export.log 2>&1
```

## 故障排除

### 问题: 导出失败，提示 "Database connection not found"

**原因**: 数据库连接不存在或已删除

**解决**:
1. 检查数据库连接列表
2. 确认数据库名称拼写正确
3. 重新创建连接（如已删除）

### 问题: Excel 导出提示 "openpyxl not installed"

**原因**: 缺少 Excel 支持库

**解决**:
```bash
cd backend
pip install openpyxl
```

### 问题: 导出历史为空

**原因**: 未运行数据库迁移

**解决**:
```bash
cd backend
alembic upgrade head
```

### 问题: 导出速度很慢

**可能原因**:

1. **查询慢**: 优化 SQL 查询
   ```sql
   -- 添加 WHERE 条件
   SELECT * FROM large_table WHERE date > '2026-01-01'

   -- 添加索引
   CREATE INDEX idx_date ON large_table(date)
   ```

2. **数据量大**: 使用 LIMIT
   ```sql
   SELECT * FROM users LIMIT 10000
   ```

3. **网络慢**: 检查网络连接

### 问题: CSV 文件损坏或格式错误

**检查清单**:

1. ✅ 文件完整下载（检查文件大小）
2. ✅ 使用正确的编码打开（UTF-8）
3. ✅ 特殊字符正确转义
4. ✅ 尝试其他文本编辑器打开

---

## 更多帮助

**文档资源**:
- 完整实现总结: `/FULL_IMPLEMENTATION_SUMMARY.md`
- 快速开始: `/EXPORT_QUICK_START.md`
- API 文档: http://localhost:8000/docs
- 设计文档: `/specs/0002-design-export.md`

**反馈和建议**:
- GitHub Issues: [项目地址]
- 邮件: support@example.com

---

**版本**: 1.0.0
**更新日期**: 2026-02-05
**适用于**: Phase 1-6 完整实现
