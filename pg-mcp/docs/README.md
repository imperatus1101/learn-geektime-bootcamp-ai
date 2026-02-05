# PostgreSQL MCP Server - 文档中心

欢迎来到 PostgreSQL MCP Server 的文档中心。本目录组织了项目的所有文档资源。

## 文档导航

### 🚀 快速开始

新用户？从这里开始：

1. **[项目 README](../README.md)** - 项目概览和基本介绍
2. **[快速开始指南](../QUICKSTART.md)** - 5 分钟快速安装和运行
3. **[Claude Desktop 配置](../CLAUDE_DESKTOP_SETUP.md)** - 与 Claude Desktop 集成

### 👨‍💻 开发文档

开发人员必读：

- **[开发指南](../CLAUDE.md)** - 代码规范、开发流程和最佳实践
- **[规范文档](../specs/README.md)** - 完整的需求、设计和测试文档
- **[API 参考](#)** - API 接口文档 (待补充)
- **[架构文档](#)** - 系统架构详解 (见 specs/0002)

### 📋 规范文档

详细的需求和设计文档：

| 文档 | 描述 | 路径 |
|------|------|------|
| PRD | 产品需求文档 | [specs/0001-pg-mcp-prd.md](../specs/0001-pg-mcp-prd.md) |
| 设计文档 | 系统架构和组件设计 | [specs/0002-pg-mcp-design.md](../specs/0002-pg-mcp-design.md) |
| 实现计划 | 开发路线图 | [specs/0004-pg-mcp-impl-plan.md](../specs/0004-pg-mcp-impl-plan.md) |
| 测试计划 | 测试策略和用例 | [specs/0007-pg-mcp-test-plan.md](../specs/0007-pg-mcp-test-plan.md) |

完整列表请参阅 [specs/README.md](../specs/README.md)。

### 🔧 运维文档

部署和维护：

- **[部署指南](#)** - 生产环境部署 (待补充)
- **[故障排查](../README.md#故障排查)** - 常见问题解决
- **[监控配置](../README.md#可观测性)** - 指标和日志配置
- **[安全最佳实践](../README.md#安全最佳实践)** - 生产环境安全建议

### 📚 参考资源

- **[MCP 协议](https://modelcontextprotocol.io)** - Model Context Protocol 官方文档
- **[FastMCP](https://github.com/jlowin/fastmcp)** - FastMCP 框架文档
- **[SQLGlot](https://github.com/tobymao/sqlglot)** - SQL 解析器文档
- **[asyncpg](https://magicstack.github.io/asyncpg/)** - PostgreSQL 驱动文档

### 📖 历史文档

开发过程中的实现总结和修复记录：

- [实现总结文档](./history/) - 各阶段开发总结

## 文档结构

```
pg-mcp/
├── README.md                     # 项目主文档
├── QUICKSTART.md                 # 快速开始指南
├── CLAUDE_DESKTOP_SETUP.md       # Claude Desktop 配置
├── CLAUDE.md                     # 开发指南
├── docs/                         # 文档中心
│   ├── README.md                 # 本文件
│   └── history/                  # 历史文档
│       ├── IMPLEMENTATION_SUMMARY.md
│       ├── PHASE6_SUMMARY.md
│       └── ...
├── specs/                        # 规范文档
│   ├── README.md                 # 规范文档索引
│   ├── 0001-pg-mcp-prd.md       # 产品需求
│   ├── 0002-pg-mcp-design.md    # 系统设计
│   └── ...
└── fixtures/                     # 测试数据文档
    └── README.md
```

## 文档贡献

### 如何贡献文档

1. 遵循 [Markdown 规范](https://www.markdownguide.org/)
2. 使用清晰的标题层次结构
3. 添加代码示例时使用语法高亮
4. 包含目录和导航链接（长文档）
5. 更新相关的索引文件

### 文档风格指南

- **语言**：中文为主，技术术语可保留英文
- **格式**：使用 Markdown 格式
- **代码示例**：提供完整的、可运行的示例
- **截图**：如需要，使用清晰的截图
- **链接**：使用相对路径链接项目内文档

## 需要帮助？

- 📧 提交 Issue: [GitHub Issues](https://github.com/yourusername/pg-mcp/issues)
- 💬 参与讨论: [GitHub Discussions](https://github.com/yourusername/pg-mcp/discussions)
- 📝 查看 FAQ: [README.md](../README.md#故障排查)

---

最后更新: 2026-02-05
