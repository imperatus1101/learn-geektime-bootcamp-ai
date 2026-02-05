# PostgreSQL MCP Server

一个生产级的 [Model Context Protocol (MCP)](https://modelcontextprotocol.io) 服务器，让你能够通过自然语言与 PostgreSQL 数据库交互。

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.14+-green.svg)](https://github.com/jlowin/fastmcp)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 核心特性

- 🗣️ **自然语言查询** - 用普通话提问，自动转换为 SQL 查询
- 🔒 **安全优先** - 只读强制、SQL 注入防护、查询超时控制
- ✅ **智能验证** - AI 驱动的结果验证和置信度评分
- ⚡ **高性能** - 连接池、Schema 缓存、异步执行
- 📊 **生产就绪** - 完整的可观测性、熔断器、限流机制
- 🔌 **MCP 兼容** - 无缝集成 Claude Desktop 和其他 MCP 客户端

## 快速开始

### 前置要求

- Python 3.12+
- PostgreSQL 12+
- OpenAI API 密钥
- [UV](https://github.com/astral-sh/uv) 包管理器（推荐）

### 5 分钟快速安装

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/pg-mcp.git
cd pg-mcp

# 2. 安装依赖
uv sync

# 3. 配置环境
cp .env.example .env
# 编辑 .env 填入你的数据库和 OpenAI 配置

# 4. 启动服务器
uv run python main.py
```

### 与 Claude Desktop 集成

将以下配置添加到 Claude Desktop 配置文件：

**配置文件位置**:
- macOS/Linux: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "postgres": {
      "command": "uv",
      "args": ["--directory", "/path/to/pg-mcp", "run", "python", "main.py"],
      "env": {
        "DATABASE_HOST": "localhost",
        "DATABASE_NAME": "mydb",
        "DATABASE_USER": "postgres",
        "DATABASE_PASSWORD": "your-password",
        "OPENAI_API_KEY": "sk-your-api-key"
      }
    }
  }
}
```

重启 Claude Desktop 即可使用。

详细安装指南请参阅 [QUICKSTART.md](./QUICKSTART.md) 和 [CLAUDE_DESKTOP_SETUP.md](./CLAUDE_DESKTOP_SETUP.md)。

## 使用示例

连接 Claude Desktop 后，你可以直接用自然语言提问：

```text
问: "数据库里有多少个表？"
答: 执行 SELECT COUNT(*) FROM information_schema.tables... → 结果: 42 个表

问: "最近 30 天注册了多少用户？"
答: 执行 SELECT COUNT(*) FROM users WHERE created_at > ... → 结果: 1,234 个用户

问: "销售额最高的前 10 个产品是什么？"
答: 执行 SELECT product_name, SUM(quantity * price) ... → 返回产品列表
```

### 返回类型

- **`result`** (默认) - 直接执行并返回查询结果
- **`sql`** - 只生成 SQL 语句，不执行

### 响应示例

**成功响应:**
```json
{
  "success": true,
  "generated_sql": "SELECT COUNT(*) FROM users",
  "data": {
    "columns": ["count"],
    "rows": [[1523]],
    "row_count": 1,
    "execution_time": 0.023
  },
  "confidence": 95
}
```

**错误响应:**
```json
{
  "success": false,
  "error": {
    "code": "SECURITY_VIOLATION",
    "message": "Query contains blocked operation: DELETE"
  }
}
```

## 系统架构

```
用户自然语言问题
        ↓
┌─────────────────┐
│  MCP Server     │ ← FastMCP 框架
└─────────────────┘
        ↓
┌─────────────────┐
│ Query           │ ← 查询协调器
│ Orchestrator    │   (重试、错误处理)
└─────────────────┘
        ↓
┌─────────────────┐     ┌─────────────┐
│ SQL Generator   │────▶│ Schema      │
│ (GPT-5.2-mini)  │     │ Cache       │
└─────────────────┘     └─────────────┘
        ↓
┌─────────────────┐
│ SQL Validator   │ ← 安全检查
│ (sqlglot)       │   (只读、注入防护)
└─────────────────┘
        ↓
┌─────────────────┐
│ SQL Executor    │ ← PostgreSQL
│ (asyncpg)       │   (连接池、超时)
└─────────────────┘
        ↓
┌─────────────────┐
│ Result          │ ← AI 验证
│ Validator       │   (置信度评分)
└─────────────────┘
        ↓
    返回结果
```

### 安全机制

- ✅ 只读模式 - 默认仅允许 SELECT 查询
- ✅ SQL 注入防护 - 使用 sqlglot 解析和验证
- ✅ 函数黑名单 - 阻止危险的 PostgreSQL 函数
- ✅ 资源限制 - 行数限制、查询超时
- ✅ 只读事务 - 所有查询在只读事务中执行

### 弹性设计

- 🔄 自动重试 - 指数退避策略
- ⚡ 熔断器 - 防止级联失败
- 🚦 限流控制 - 保护 API 配额
- 💾 连接池 - 高效的数据库连接复用
- ⏱️ Schema 缓存 - 减少元数据查询

## 配置

### 核心配置项

| 环境变量 | 描述 | 默认值 |
|---------|------|--------|
| `DATABASE_HOST` | PostgreSQL 主机地址 | `localhost` |
| `DATABASE_NAME` | 数据库名称 | 必需 |
| `DATABASE_USER` | 数据库用户名 | 必需 |
| `DATABASE_PASSWORD` | 数据库密码 | 必需 |
| `OPENAI_API_KEY` | OpenAI API 密钥 | 必需 |
| `OPENAI_MODEL` | 使用的模型 | `gpt-5.2-mini` |
| `SECURITY_MAX_ROWS` | 最大返回行数 | `10000` |
| `SECURITY_MAX_EXECUTION_TIME` | 查询超时(秒) | `30` |

完整配置选项请参考 [.env.example](./.env.example) 文件。

### 配置文件位置

项目支持多种配置方式（按优先级排序）：

1. 环境变量
2. `.env` 文件
3. Claude Desktop 配置中的 `env` 字段
4. 默认值

## 开发指南

### 开发环境设置

```bash
# 克隆并安装开发依赖
git clone https://github.com/yourusername/pg-mcp.git
cd pg-mcp
uv sync --all-extras

# 安装 pre-commit hooks (可选)
pre-commit install
```

### 测试

```bash
# 运行所有测试
uv run pytest

# 运行测试并生成覆盖率报告
uv run pytest --cov=src --cov-report=html

# 运行特定类别测试
uv run pytest tests/unit/              # 单元测试
uv run pytest tests/integration/       # 集成测试
uv run pytest -m security              # 安全测试
```

### 代码质量检查

```bash
# 类型检查
uv run mypy src

# 代码检查和格式化
uv run ruff check --fix .
uv run ruff format .
```

### 项目结构

```
pg-mcp/
├── src/pg_mcp/              # 源代码
│   ├── services/            # 核心服务层
│   ├── models/              # 数据模型
│   ├── config/              # 配置管理
│   ├── db/                  # 数据库层
│   └── observability/       # 可观测性
├── tests/                   # 测试代码
│   ├── unit/                # 单元测试
│   ├── integration/         # 集成测试
│   └── e2e/                 # 端到端测试
├── specs/                   # 规范文档
├── fixtures/                # 测试数据
└── main.py                  # 入口文件
```

详细开发指南请参阅 [CLAUDE.md](./CLAUDE.md)。

## 部署

### Docker 部署

```bash
# 使用 Docker Compose (推荐)
docker-compose up -d

# 或手动构建和运行
docker build -t pg-mcp:latest .
docker run -d --name pg-mcp \
  -e DATABASE_HOST=your-host \
  -e DATABASE_NAME=your-db \
  -e OPENAI_API_KEY=sk-your-key \
  pg-mcp:latest
```

### 生产环境建议

1. **使用只读数据库用户**
2. **启用 HTTPS** (如果暴露 API)
3. **配置监控和告警**
4. **定期备份配置文件**
5. **使用密钥管理服务**

详细部署指南请参阅 [deployment docs](./docs/deployment.md)。

## 可观测性

### Prometheus 指标

服务器在端口 9090 暴露 Prometheus 指标：

```bash
curl http://localhost:9090/metrics
```

主要指标：
- `pg_mcp_queries_total` - 查询总数
- `pg_mcp_query_duration_seconds` - 查询耗时
- `pg_mcp_sql_validation_failures_total` - 验证失败次数
- `pg_mcp_llm_tokens_used_total` - Token 使用量

### 结构化日志

输出 JSON 格式的结构化日志：

```json
{
  "timestamp": "2026-02-05T10:30:00Z",
  "level": "INFO",
  "message": "Query executed",
  "execution_time": 0.023,
  "row_count": 42
}
```

## 故障排查

### 常见问题

| 问题 | 解决方案 |
|------|---------|
| 数据库连接失败 | 检查 DATABASE_* 配置，确认 PostgreSQL 正在运行 |
| OpenAI API 错误 | 验证 API 密钥有效且有足够配额 |
| 查询超时 | 增加 SECURITY_MAX_EXECUTION_TIME 或优化查询 |
| Schema 缓存失效 | 重启服务器或检查数据库权限 |

### 调试模式

```bash
# 启用详细日志
export OBSERVABILITY_LOG_LEVEL=DEBUG
uv run python main.py
```

更多故障排查信息请参阅 [Troubleshooting Guide](./docs/troubleshooting.md)。

## 文档

### 快速导航

- 📖 [快速开始指南](./QUICKSTART.md) - 5 分钟快速上手
- 🔧 [Claude Desktop 配置](./CLAUDE_DESKTOP_SETUP.md) - Claude Desktop 集成详细说明
- 👨‍💻 [开发指南](./CLAUDE.md) - 开发规范和最佳实践
- 📋 [规范文档](./specs/README.md) - 完整的需求、设计和测试文档

### 主要文档

| 文档 | 描述 |
|------|------|
| [PRD](./specs/0001-pg-mcp-prd.md) | 产品需求文档 |
| [系统设计](./specs/0002-pg-mcp-design.md) | 架构和组件设计 |
| [实现计划](./specs/0004-pg-mcp-impl-plan.md) | 开发路线图 |
| [测试计划](./specs/0007-pg-mcp-test-plan.md) | 测试策略和用例 |

## 安全最佳实践

### 生产环境建议

1. **创建只读数据库用户**

```sql
CREATE USER pg_mcp_readonly WITH PASSWORD 'secure-password';
GRANT CONNECT ON DATABASE your_db TO pg_mcp_readonly;
GRANT USAGE ON SCHEMA public TO pg_mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO pg_mcp_readonly;
```

2. **保护 API 密钥** - 使用环境变量或密钥管理服务
3. **网络隔离** - 通过防火墙限制数据库访问
4. **启用监控** - 为异常查询模式设置告警
5. **定期审计** - 检查查询日志和访问模式

## 贡献

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

详细贡献指南请参阅 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](./LICENSE) 文件。

## 致谢

- [FastMCP](https://github.com/jlowin/fastmcp) - MCP 框架
- [sqlglot](https://github.com/tobymao/sqlglot) - SQL 解析器
- [asyncpg](https://github.com/MagicStack/asyncpg) - PostgreSQL 驱动

## 支持

- 📧 Issues: [GitHub Issues](https://github.com/yourusername/pg-mcp/issues)
- 📚 文档: [specs/](./specs/)
- 💬 讨论: [GitHub Discussions](https://github.com/yourusername/pg-mcp/discussions)

---

**注意**: 本项目处于活跃开发中。生产环境使用前请仔细测试。
