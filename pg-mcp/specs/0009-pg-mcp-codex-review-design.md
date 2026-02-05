# PostgreSQL MCP Server - 代码评审改进详细设计

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档版本 | v1.0 |
| 创建日期 | 2026-02-05 |
| 基于文档 | pg-mcp-代码评审报告.md |
| 设计规范 | 0002-pg-mcp-design.md |
| 作者 | 开发团队 |

---

## 目录

1. [概述](#概述)
2. [代码质量问题修复](#代码质量问题修复)
3. [缺失组件详细设计](#缺失组件详细设计)
4. [架构合规性改进](#架构合规性改进)
5. [实施计划](#实施计划)
6. [验收标准](#验收标准)
7. [风险评估](#风险评估)

---

## 概述

### 设计目标

基于代码评审报告的发现，本设计文档提供了全面的改进方案，目标是：

1. **修复代码质量问题**：消除重复代码、未使用配置、类冲突等问题
2. **补全缺失组件**：实现多数据库支持、韧性层、可观测性集成
3. **提升架构合规性**：确保实现与设计规范一致
4. **增强安全性**：完善安全配置和验证机制
5. **改进可测试性**：添加 mock 支持和确定性测试

### 改进范围

| 类别 | 问题数量 | 优先级 |
|------|----------|--------|
| 代码质量问题 | 4 | P3 |
| 缺失组件 | 4 大类 | P1-P2 |
| 安全问题 | 4 | P1 |
| 测试缺口 | 6+ | P4 |

---

## 代码质量问题修复

### CQ-1：重复方法定义修复

#### 问题描述

**位置**：`src/pg_mcp/models/query.py:160-220`

**问题**：
- `QueryResponse.to_dict()` 方法有两个定义
- 第二个定义覆盖第一个，导致 `tokens_used` 可能被省略

**影响**：
- 死代码存在
- API 响应不一致
- 客户端无法可靠获取 token 使用信息

#### 解决方案

##### 设计决策

**选择**：保留包含完整字段的单一 `to_dict()` 实现

**理由**：
1. `tokens_used` 对于成本跟踪至关重要
2. API 响应应该完整且可预测
3. 简化代码维护

##### 实现方案

```python
# src/pg_mcp/models/query.py

from pydantic import BaseModel, Field
from typing import Any

class QueryResponse(BaseModel):
    """查询响应模型"""

    success: bool = Field(..., description="查询是否成功")
    data: QueryResult | None = Field(None, description="查询结果数据")
    error: ErrorDetail | None = Field(None, description="错误信息")
    sql: str | None = Field(None, description="生成的 SQL 语句")
    confidence: int | None = Field(None, description="结果置信度 (0-100)")
    tokens_used: int | None = Field(None, description="LLM 使用的 token 数")

    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典格式，包含所有非 None 字段

        Returns:
            包含所有有效字段的字典
        """
        result: dict[str, Any] = {
            "success": self.success,
        }

        if self.data is not None:
            result["data"] = self.data.model_dump()

        if self.error is not None:
            result["error"] = self.error.model_dump()

        if self.sql is not None:
            result["sql"] = self.sql

        if self.confidence is not None:
            result["confidence"] = self.confidence

        # 始终包含 tokens_used（即使为 None，也应该体现出来）
        result["tokens_used"] = self.tokens_used

        return result
```

##### 测试方案

```python
# tests/unit/test_models.py

import pytest
from src.pg_mcp.models.query import QueryResponse, QueryResult, ErrorDetail

class TestQueryResponse:
    """QueryResponse 模型测试"""

    def test_to_dict_includes_all_fields(self):
        """测试 to_dict 包含所有字段"""
        response = QueryResponse(
            success=True,
            data=QueryResult(
                columns=["id", "name"],
                rows=[[1, "test"]],
                row_count=1,
            ),
            sql="SELECT * FROM users",
            confidence=95,
            tokens_used=150,
        )

        result = response.to_dict()

        assert result["success"] is True
        assert "data" in result
        assert result["sql"] == "SELECT * FROM users"
        assert result["confidence"] == 95
        assert result["tokens_used"] == 150

    def test_to_dict_always_includes_tokens_used(self):
        """测试 to_dict 始终包含 tokens_used，即使为 None"""
        response = QueryResponse(success=False)
        result = response.to_dict()

        assert "tokens_used" in result
        assert result["tokens_used"] is None

    def test_to_dict_with_error(self):
        """测试错误响应的 to_dict"""
        response = QueryResponse(
            success=False,
            error=ErrorDetail(
                code="SQL_PARSE_ERROR",
                message="Invalid SQL syntax",
            ),
            tokens_used=50,
        )

        result = response.to_dict()

        assert result["success"] is False
        assert "error" in result
        assert result["tokens_used"] == 50
```

---

### CQ-2：ErrorDetail 类冲突解决

#### 问题描述

**位置**：
- `src/pg_mcp/models/errors.py`（普通 Python 类）
- `src/pg_mcp/models/query.py:139-214`（Pydantic 模型）

**问题**：
- 两个不同的 `ErrorDetail` 定义
- `errors.py` 中的类未被使用
- 导致代码混乱和维护困难

#### 解决方案

##### 设计决策

**选择**：统一使用 Pydantic `ErrorDetail` 模型

**理由**：
1. 与 `QueryResponse` 集成更好
2. 自动序列化/反序列化
3. 内置验证
4. 符合项目类型安全原则

##### 实现方案

**步骤 1**：在 `models/errors.py` 中定义统一的 ErrorDetail

```python
# src/pg_mcp/models/errors.py

from enum import StrEnum, auto
from pydantic import BaseModel, Field

class ErrorCode(StrEnum):
    """错误码枚举"""

    # 成功
    SUCCESS = auto()

    # 安全相关
    SECURITY_VIOLATION = auto()
    BLOCKED_OPERATION = auto()
    BLOCKED_FUNCTION = auto()
    BLOCKED_TABLE = auto()
    BLOCKED_COLUMN = auto()

    # SQL 相关
    SQL_PARSE_ERROR = auto()
    SQL_GENERATION_ERROR = auto()
    SQL_VALIDATION_ERROR = auto()

    # 数据库相关
    DATABASE_ERROR = auto()
    DATABASE_CONNECTION_ERROR = auto()
    DATABASE_NOT_FOUND = auto()
    EXECUTION_TIMEOUT = auto()

    # LLM 相关
    LLM_ERROR = auto()
    LLM_TIMEOUT = auto()
    LLM_UNAVAILABLE = auto()
    LLM_RATE_LIMIT = auto()

    # 验证相关
    VALIDATION_ERROR = auto()
    LOW_CONFIDENCE = auto()
    RESULT_MISMATCH = auto()

    # 限流相关
    RATE_LIMIT_EXCEEDED = auto()

    # 系统相关
    INTERNAL_ERROR = auto()
    CONFIGURATION_ERROR = auto()


class ErrorDetail(BaseModel):
    """
    统一错误详情模型

    用于所有错误响应，提供一致的错误信息结构
    """

    code: ErrorCode = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    details: dict[str, Any] | None = Field(None, description="额外的错误详情")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "SQL_PARSE_ERROR",
                    "message": "Invalid SQL syntax near 'FORM'",
                    "details": {"position": 15, "token": "FORM"}
                }
            ]
        }
    }


# 异常类层次结构
class PgMcpError(Exception):
    """基础异常类"""

    def __init__(self, message: str, code: ErrorCode, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_error_detail(self) -> ErrorDetail:
        """转换为 ErrorDetail 模型"""
        return ErrorDetail(
            code=self.code,
            message=self.message,
            details=self.details if self.details else None,
        )


class SecurityViolationError(PgMcpError):
    """安全违规异常"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, ErrorCode.SECURITY_VIOLATION, details)


class SQLParseError(PgMcpError):
    """SQL 解析异常"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, ErrorCode.SQL_PARSE_ERROR, details)


class DatabaseError(PgMcpError):
    """数据库异常"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, ErrorCode.DATABASE_ERROR, details)


class LLMError(PgMcpError):
    """LLM 异常"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, ErrorCode.LLM_ERROR, details)


class LLMTimeoutError(LLMError):
    """LLM 超时异常"""

    def __init__(self, message: str = "LLM request timed out"):
        super().__init__(message, ErrorCode.LLM_TIMEOUT)


class LLMUnavailableError(LLMError):
    """LLM 不可用异常"""

    def __init__(self, message: str = "LLM service unavailable"):
        super().__init__(message, ErrorCode.LLM_UNAVAILABLE)


class ExecutionTimeoutError(PgMcpError):
    """执行超时异常"""

    def __init__(self, message: str = "Query execution timed out"):
        super().__init__(message, ErrorCode.EXECUTION_TIMEOUT)


class RateLimitExceededError(PgMcpError):
    """速率限制异常"""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, ErrorCode.RATE_LIMIT_EXCEEDED)
```

**步骤 2**：更新 `models/query.py` 以使用统一的 ErrorDetail

```python
# src/pg_mcp/models/query.py

from pydantic import BaseModel, Field
from typing import Any
from .errors import ErrorDetail  # 导入统一的 ErrorDetail

# 删除 query.py 中的 ErrorDetail 定义

class QueryResponse(BaseModel):
    """查询响应模型"""

    success: bool = Field(..., description="查询是否成功")
    data: QueryResult | None = Field(None, description="查询结果数据")
    error: ErrorDetail | None = Field(None, description="错误信息")
    sql: str | None = Field(None, description="生成的 SQL 语句")
    confidence: int | None = Field(None, description="结果置信度 (0-100)")
    tokens_used: int | None = Field(None, description="LLM 使用的 token 数")
```

##### 测试方案

```python
# tests/unit/test_errors.py

import pytest
from src.pg_mcp.models.errors import (
    ErrorCode,
    ErrorDetail,
    PgMcpError,
    SecurityViolationError,
    SQLParseError,
)

class TestErrorDetail:
    """ErrorDetail 模型测试"""

    def test_error_detail_creation(self):
        """测试创建 ErrorDetail"""
        error = ErrorDetail(
            code=ErrorCode.SQL_PARSE_ERROR,
            message="Invalid SQL",
            details={"position": 10},
        )

        assert error.code == ErrorCode.SQL_PARSE_ERROR
        assert error.message == "Invalid SQL"
        assert error.details == {"position": 10}

    def test_error_detail_without_details(self):
        """测试不带详情的 ErrorDetail"""
        error = ErrorDetail(
            code=ErrorCode.DATABASE_ERROR,
            message="Connection failed",
        )

        assert error.code == ErrorCode.DATABASE_ERROR
        assert error.details is None


class TestExceptionHierarchy:
    """异常类层次结构测试"""

    def test_security_violation_error(self):
        """测试安全违规异常"""
        error = SecurityViolationError("DROP TABLE blocked")

        assert isinstance(error, PgMcpError)
        assert error.code == ErrorCode.SECURITY_VIOLATION
        assert "DROP TABLE" in error.message

    def test_exception_to_error_detail(self):
        """测试异常转换为 ErrorDetail"""
        error = SQLParseError(
            "Invalid syntax",
            details={"token": "FORM"}
        )

        error_detail = error.to_error_detail()

        assert isinstance(error_detail, ErrorDetail)
        assert error_detail.code == ErrorCode.SQL_PARSE_ERROR
        assert error_detail.message == "Invalid syntax"
        assert error_detail.details == {"token": "FORM"}
```

---

### CQ-3：冗余断路器实例化修复

#### 问题描述

**位置**：
- `src/pg_mcp/server.py:177-185`（服务器级）
- `src/pg_mcp/services/orchestrator.py:98-103`（编排器级）

**问题**：
- 断路器在两处实例化
- 服务器级实例从未使用
- 造成资源浪费和混乱

#### 解决方案

##### 设计决策

**选择**：使用依赖注入，在服务器级创建共享实例

**理由**：
1. 单一真实来源
2. 便于测试（可以注入 mock）
3. 符合 SOLID 原则中的依赖反转
4. 资源高效

##### 实现方案

**步骤 1**：在 server.py 中创建共享断路器

```python
# src/pg_mcp/server.py

from contextlib import asynccontextmanager
from fastmcp import FastMCP
from .resilience.circuit_breaker import CircuitBreaker
from .resilience.rate_limiter import MultiRateLimiter
from .services.orchestrator import QueryOrchestrator
from .config.settings import Settings

# 全局服务实例
_circuit_breaker: CircuitBreaker | None = None
_rate_limiter: MultiRateLimiter | None = None
_orchestrator: QueryOrchestrator | None = None

@asynccontextmanager
async def lifespan(app: FastMCP):
    """
    服务器生命周期管理

    负责初始化和清理所有共享资源
    """
    global _circuit_breaker, _rate_limiter, _orchestrator

    settings = Settings()

    # 创建共享的韧性组件
    _circuit_breaker = CircuitBreaker(
        failure_threshold=settings.resilience.circuit_breaker_threshold,
        recovery_timeout=settings.resilience.circuit_breaker_timeout,
        half_open_max_calls=settings.resilience.circuit_breaker_half_open_calls,
    )

    _rate_limiter = MultiRateLimiter(
        default_rate=settings.resilience.rate_limit_per_second,
        default_burst=settings.resilience.rate_limit_burst,
    )

    # 初始化数据库连接池
    pools = await create_pools(settings)

    # 创建执行器映射（支持多数据库）
    executors = {
        db_name: SQLExecutor(
            pool=pool,
            security_config=settings.security,
        )
        for db_name, pool in pools.items()
    }

    # 创建编排器（注入共享组件）
    _orchestrator = QueryOrchestrator(
        settings=settings,
        executors=executors,
        circuit_breaker=_circuit_breaker,  # 注入共享断路器
        rate_limiter=_rate_limiter,        # 注入共享速率限制器
    )

    try:
        yield
    finally:
        # 清理资源
        for pool in pools.values():
            await pool.close()

        _circuit_breaker = None
        _rate_limiter = None
        _orchestrator = None


# 创建 MCP 服务器
mcp = FastMCP("pg-mcp", lifespan=lifespan)


@mcp.tool()
async def query_postgres(question: str, database: str | None = None) -> dict:
    """
    自然语言查询 PostgreSQL 数据库

    Args:
        question: 自然语言问题
        database: 目标数据库名称（可选）

    Returns:
        查询结果字典
    """
    if _orchestrator is None:
        raise RuntimeError("Service not initialized")

    response = await _orchestrator.query(question=question, database=database)
    return response.to_dict()
```

**步骤 2**：更新 orchestrator.py 以接受注入的组件

```python
# src/pg_mcp/services/orchestrator.py

from typing import Dict
from ..resilience.circuit_breaker import CircuitBreaker
from ..resilience.rate_limiter import MultiRateLimiter
from ..config.settings import Settings
from .sql_executor import SQLExecutor

class QueryOrchestrator:
    """
    查询编排服务

    负责协调 SQL 生成、验证、执行和结果验证的完整流程
    """

    def __init__(
        self,
        settings: Settings,
        executors: Dict[str, SQLExecutor],
        circuit_breaker: CircuitBreaker,  # 注入而非创建
        rate_limiter: MultiRateLimiter,   # 注入而非创建
    ):
        """
        初始化编排器

        Args:
            settings: 配置对象
            executors: 数据库名称到执行器的映射
            circuit_breaker: 共享的断路器实例
            rate_limiter: 共享的速率限制器实例
        """
        self._settings = settings
        self._executors = executors
        self._circuit_breaker = circuit_breaker
        self._rate_limiter = rate_limiter

        # 初始化其他服务
        self._generator = SQLGenerator(settings.openai)
        self._validator = SQLValidator(settings.security)
        self._result_validator = ResultValidator(settings.openai)

    async def query(self, question: str, database: str | None = None) -> QueryResponse:
        """执行查询"""
        # 使用注入的 circuit_breaker 和 rate_limiter
        # ...
```

##### 测试方案

```python
# tests/unit/test_orchestrator.py

import pytest
from unittest.mock import Mock, AsyncMock
from src.pg_mcp.services.orchestrator import QueryOrchestrator
from src.pg_mcp.resilience.circuit_breaker import CircuitBreaker
from src.pg_mcp.resilience.rate_limiter import MultiRateLimiter

@pytest.fixture
def mock_circuit_breaker():
    """Mock 断路器"""
    cb = Mock(spec=CircuitBreaker)
    cb.call = AsyncMock(side_effect=lambda f: f())
    return cb

@pytest.fixture
def mock_rate_limiter():
    """Mock 速率限制器"""
    rl = Mock(spec=MultiRateLimiter)
    rl.acquire = AsyncMock()
    return rl

@pytest.fixture
def orchestrator(mock_circuit_breaker, mock_rate_limiter, mock_settings):
    """创建测试用编排器"""
    return QueryOrchestrator(
        settings=mock_settings,
        executors={},
        circuit_breaker=mock_circuit_breaker,
        rate_limiter=mock_rate_limiter,
    )

class TestOrchestratorDependencyInjection:
    """测试依赖注入"""

    def test_orchestrator_uses_injected_circuit_breaker(
        self, orchestrator, mock_circuit_breaker
    ):
        """测试使用注入的断路器"""
        assert orchestrator._circuit_breaker is mock_circuit_breaker

    def test_orchestrator_uses_injected_rate_limiter(
        self, orchestrator, mock_rate_limiter
    ):
        """测试使用注入的速率限制器"""
        assert orchestrator._rate_limiter is mock_rate_limiter
```

---

### CQ-4：未使用配置字段处理

#### 问题描述

**位置**：
- `src/pg_mcp/config/settings.py:88-112`

**问题**：
- `ResilienceConfig` 的 `retry_delay` 和 `backoff_factor` 字段定义但未使用
- 没有对应的重试逻辑实现

#### 解决方案

##### 设计决策

**选择**：实现完整的重试逻辑以使用这些配置

**理由**：
1. 配置字段已经设计好
2. 重试机制对韧性至关重要
3. 与设计规范一致

详细设计见 [MC-2：重试/退避机制实现](#mc-2重试退避机制实现)

---

## 缺失组件详细设计

### MC-1：多数据库支持实现

#### 背景

**设计规范要求**：支持连接多个 PostgreSQL 数据库

**当前实现**：
- 单一 `database` 配置对象
- 单一连接池和执行器
- 无法路由到不同数据库

#### 设计方案

##### 配置模型改进

```python
# src/pg_mcp/config/settings.py

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class DatabaseConfig(BaseModel):
    """单个数据库配置"""

    name: str = Field(..., description="数据库名称（唯一标识）")
    host: str = Field(..., description="数据库主机")
    port: int = Field(5432, description="数据库端口")
    database: str = Field(..., description="数据库名称")
    user: str = Field(..., description="数据库用户")
    password: str = Field(..., description="数据库密码")

    # 连接池配置
    min_pool_size: int = Field(5, ge=1, description="最小连接数")
    max_pool_size: int = Field(20, ge=1, le=100, description="最大连接数")
    pool_timeout: float = Field(30.0, gt=0, description="连接超时（秒）")

    # 查询配置
    query_timeout: float = Field(30.0, gt=0, description="查询超时（秒）")
    max_rows: int = Field(1000, ge=1, description="最大返回行数")


class Settings(BaseSettings):
    """应用配置"""

    # 多数据库配置
    databases: list[DatabaseConfig] = Field(
        ...,
        min_length=1,
        description="数据库配置列表"
    )

    # 默认数据库
    default_database: str = Field(
        ...,
        description="默认数据库名称（必须在 databases 列表中）"
    )

    # 其他配置...
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    resilience: ResilienceConfig = Field(default_factory=ResilienceConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )

    def model_post_init(self, __context):
        """验证配置一致性"""
        # 验证默认数据库存在
        db_names = {db.name for db in self.databases}
        if self.default_database not in db_names:
            raise ValueError(
                f"默认数据库 '{self.default_database}' "
                f"不在数据库列表中: {db_names}"
            )

        # 验证数据库名称唯一性
        if len(db_names) != len(self.databases):
            raise ValueError("数据库名称必须唯一")
```

##### 数据库池管理改进

```python
# src/pg_mcp/db/pool.py

import asyncpg
from typing import Dict
from ..config.settings import DatabaseConfig, Settings

async def create_pool(config: DatabaseConfig) -> asyncpg.Pool:
    """
    创建单个数据库连接池

    Args:
        config: 数据库配置

    Returns:
        asyncpg 连接池
    """
    dsn = (
        f"postgresql://{config.user}:{config.password}"
        f"@{config.host}:{config.port}/{config.database}"
    )

    pool = await asyncpg.create_pool(
        dsn=dsn,
        min_size=config.min_pool_size,
        max_size=config.max_pool_size,
        command_timeout=config.query_timeout,
        timeout=config.pool_timeout,
    )

    if pool is None:
        raise RuntimeError(f"Failed to create pool for database '{config.name}'")

    return pool


async def create_pools(settings: Settings) -> Dict[str, asyncpg.Pool]:
    """
    为所有配置的数据库创建连接池

    Args:
        settings: 应用配置

    Returns:
        数据库名称到连接池的映射

    Raises:
        RuntimeError: 如果任何连接池创建失败
    """
    pools: Dict[str, asyncpg.Pool] = {}

    try:
        for db_config in settings.databases:
            pool = await create_pool(db_config)
            pools[db_config.name] = pool
    except Exception as e:
        # 清理已创建的连接池
        for pool in pools.values():
            await pool.close()
        raise RuntimeError(f"Failed to initialize database pools: {e}") from e

    return pools


async def close_pools(pools: Dict[str, asyncpg.Pool]) -> None:
    """
    关闭所有连接池

    Args:
        pools: 连接池映射
    """
    for name, pool in pools.items():
        try:
            await pool.close()
        except Exception as e:
            # 记录错误但继续关闭其他池
            print(f"Error closing pool for database '{name}': {e}")
```

##### 执行器管理改进

```python
# src/pg_mcp/services/sql_executor.py

import asyncpg
from typing import Dict
from ..config.settings import SecurityConfig

class SQLExecutor:
    """SQL 执行器（单数据库）"""

    def __init__(
        self,
        pool: asyncpg.Pool,
        security_config: SecurityConfig,
        database_name: str,
    ):
        """
        初始化执行器

        Args:
            pool: 数据库连接池
            security_config: 安全配置
            database_name: 数据库名称（用于日志）
        """
        self._pool = pool
        self._security_config = security_config
        self._database_name = database_name

    async def execute(self, sql: str) -> QueryResult:
        """执行 SQL 查询"""
        # 实现...


class ExecutorManager:
    """执行器管理器（多数据库）"""

    def __init__(
        self,
        executors: Dict[str, SQLExecutor],
        default_database: str,
    ):
        """
        初始化管理器

        Args:
            executors: 数据库名称到执行器的映射
            default_database: 默认数据库名称
        """
        self._executors = executors
        self._default_database = default_database

    def get_executor(self, database: str | None = None) -> SQLExecutor:
        """
        获取指定数据库的执行器

        Args:
            database: 数据库名称，None 表示使用默认数据库

        Returns:
            SQL 执行器

        Raises:
            ValueError: 如果数据库不存在
        """
        db_name = database or self._default_database

        if db_name not in self._executors:
            available = list(self._executors.keys())
            raise ValueError(
                f"Database '{db_name}' not found. "
                f"Available databases: {available}"
            )

        return self._executors[db_name]

    def list_databases(self) -> list[str]:
        """列出所有可用数据库"""
        return list(self._executors.keys())
```

##### 编排器集成

```python
# src/pg_mcp/services/orchestrator.py

from .sql_executor import ExecutorManager

class QueryOrchestrator:
    """查询编排服务"""

    def __init__(
        self,
        settings: Settings,
        executor_manager: ExecutorManager,  # 使用管理器而非单一执行器
        circuit_breaker: CircuitBreaker,
        rate_limiter: MultiRateLimiter,
    ):
        self._settings = settings
        self._executor_manager = executor_manager
        self._circuit_breaker = circuit_breaker
        self._rate_limiter = rate_limiter

        # 初始化其他服务...

    async def query(
        self,
        question: str,
        database: str | None = None,
        return_type: str = "result",
    ) -> QueryResponse:
        """
        执行查询

        Args:
            question: 自然语言问题
            database: 目标数据库名称
            return_type: 返回类型（"result" 或 "sql"）
        """
        try:
            # 获取对应数据库的执行器
            executor = self._executor_manager.get_executor(database)

            # 生成 SQL
            sql = await self._generate_sql(question, database)

            if return_type == "sql":
                return QueryResponse(
                    success=True,
                    sql=sql,
                )

            # 执行查询
            result = await executor.execute(sql)

            return QueryResponse(
                success=True,
                data=result,
                sql=sql,
            )

        except ValueError as e:
            # 数据库不存在
            return QueryResponse(
                success=False,
                error=ErrorDetail(
                    code=ErrorCode.DATABASE_NOT_FOUND,
                    message=str(e),
                ),
            )
```

##### 环境配置示例

```bash
# .env

# 数据库配置（JSON 格式）
DATABASES='[
  {
    "name": "main",
    "host": "localhost",
    "port": 5432,
    "database": "myapp",
    "user": "postgres",
    "password": "secret",
    "min_pool_size": 5,
    "max_pool_size": 20,
    "query_timeout": 30.0,
    "max_rows": 1000
  },
  {
    "name": "analytics",
    "host": "analytics.example.com",
    "port": 5432,
    "database": "analytics",
    "user": "readonly",
    "password": "readonly_secret",
    "min_pool_size": 2,
    "max_pool_size": 10,
    "query_timeout": 60.0,
    "max_rows": 5000
  }
]'

DEFAULT_DATABASE=main
```

##### 测试方案

```python
# tests/unit/test_multi_database.py

import pytest
from src.pg_mcp.services.sql_executor import ExecutorManager

class TestExecutorManager:
    """执行器管理器测试"""

    def test_get_default_executor(self, mock_executors):
        """测试获取默认执行器"""
        manager = ExecutorManager(mock_executors, default_database="main")

        executor = manager.get_executor()

        assert executor is mock_executors["main"]

    def test_get_specific_executor(self, mock_executors):
        """测试获取指定数据库执行器"""
        manager = ExecutorManager(mock_executors, default_database="main")

        executor = manager.get_executor("analytics")

        assert executor is mock_executors["analytics"]

    def test_get_nonexistent_executor_raises(self, mock_executors):
        """测试获取不存在的数据库抛出异常"""
        manager = ExecutorManager(mock_executors, default_database="main")

        with pytest.raises(ValueError, match="Database 'invalid' not found"):
            manager.get_executor("invalid")

    def test_list_databases(self, mock_executors):
        """测试列出所有数据库"""
        manager = ExecutorManager(mock_executors, default_database="main")

        databases = manager.list_databases()

        assert set(databases) == {"main", "analytics"}
```

---

### MC-2：重试/退避机制实现

#### 背景

**设计规范要求**：在瞬态故障时自动重试

**当前实现**：
- `ResilienceConfig` 有重试配置但未使用
- 没有 `resilience/retry.py` 模块
- 编排器中没有重试逻辑

#### 设计方案

##### 重试装饰器实现

```python
# src/pg_mcp/resilience/retry.py

import asyncio
import functools
from typing import TypeVar, Callable, Any, Type
from collections.abc import Awaitable
import structlog

logger = structlog.get_logger()

T = TypeVar("T")


class RetryConfig:
    """重试配置"""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        retriable_exceptions: tuple[Type[Exception], ...] = (Exception,),
    ):
        """
        初始化重试配置

        Args:
            max_attempts: 最大尝试次数（包括首次）
            initial_delay: 初始重试延迟（秒）
            backoff_factor: 退避因子（指数退避）
            max_delay: 最大重试延迟（秒）
            retriable_exceptions: 可重试的异常类型元组
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.retriable_exceptions = retriable_exceptions

    def calculate_delay(self, attempt: int) -> float:
        """
        计算重试延迟（指数退避）

        Args:
            attempt: 当前尝试次数（从 0 开始）

        Returns:
            延迟秒数
        """
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)


class RetryExhaustedError(Exception):
    """重试次数耗尽异常"""

    def __init__(self, attempts: int, last_error: Exception):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Retry exhausted after {attempts} attempts. "
            f"Last error: {last_error}"
        )


def with_retry(config: RetryConfig):
    """
    异步函数重试装饰器

    使用指数退避策略自动重试失败的异步函数调用

    Args:
        config: 重试配置

    Example:
        @with_retry(RetryConfig(max_attempts=3, initial_delay=1.0))
        async def call_api():
            # API 调用可能失败
            ...
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(config.max_attempts):
                try:
                    result = await func(*args, **kwargs)

                    if attempt > 0:
                        logger.info(
                            "retry_succeeded",
                            function=func.__name__,
                            attempt=attempt + 1,
                            total_attempts=config.max_attempts,
                        )

                    return result

                except config.retriable_exceptions as e:
                    last_exception = e

                    is_last_attempt = (attempt == config.max_attempts - 1)

                    if is_last_attempt:
                        logger.error(
                            "retry_exhausted",
                            function=func.__name__,
                            attempts=config.max_attempts,
                            error=str(e),
                        )
                        raise RetryExhaustedError(
                            attempts=config.max_attempts,
                            last_error=e,
                        ) from e

                    delay = config.calculate_delay(attempt)

                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_attempts=config.max_attempts,
                        delay=delay,
                        error=str(e),
                    )

                    await asyncio.sleep(delay)

            # 理论上不会到达这里，但为了类型检查
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


async def retry_async(
    func: Callable[..., Awaitable[T]],
    config: RetryConfig,
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    函数式重试辅助函数

    不使用装饰器，直接重试异步函数调用

    Args:
        func: 要重试的异步函数
        config: 重试配置
        *args: 函数位置参数
        **kwargs: 函数关键字参数

    Returns:
        函数返回值

    Raises:
        RetryExhaustedError: 如果所有重试都失败

    Example:
        result = await retry_async(
            call_api,
            RetryConfig(max_attempts=3),
            url="https://api.example.com",
        )
    """
    @with_retry(config)
    async def _wrapper():
        return await func(*args, **kwargs)

    return await _wrapper()
```

##### 编排器集成

```python
# src/pg_mcp/services/orchestrator.py

from ..resilience.retry import RetryConfig, with_retry, RetryExhaustedError
from ..models.errors import LLMTimeoutError, LLMUnavailableError, DatabaseError

class QueryOrchestrator:
    """查询编排服务"""

    def __init__(
        self,
        settings: Settings,
        executor_manager: ExecutorManager,
        circuit_breaker: CircuitBreaker,
        rate_limiter: MultiRateLimiter,
    ):
        self._settings = settings
        self._executor_manager = executor_manager
        self._circuit_breaker = circuit_breaker
        self._rate_limiter = rate_limiter

        # 初始化重试配置
        self._llm_retry_config = RetryConfig(
            max_attempts=settings.resilience.max_retries,
            initial_delay=settings.resilience.retry_delay,
            backoff_factor=settings.resilience.backoff_factor,
            retriable_exceptions=(LLMTimeoutError, LLMUnavailableError),
        )

        self._db_retry_config = RetryConfig(
            max_attempts=settings.resilience.max_retries,
            initial_delay=settings.resilience.retry_delay,
            backoff_factor=settings.resilience.backoff_factor,
            retriable_exceptions=(DatabaseError,),  # 仅重试瞬态数据库错误
        )

        # 初始化其他服务...

    @with_retry
    async def _generate_sql_with_retry(
        self,
        question: str,
        schema: DatabaseSchema,
    ) -> str:
        """
        带重试的 SQL 生成

        使用装饰器自动处理 LLM 瞬态故障
        """
        return await self._generator.generate(question, schema)

    async def query(
        self,
        question: str,
        database: str | None = None,
        return_type: str = "result",
    ) -> QueryResponse:
        """执行查询（带完整重试逻辑）"""
        try:
            # 验证问题长度
            if len(question) > self._settings.validation.max_question_length:
                return QueryResponse(
                    success=False,
                    error=ErrorDetail(
                        code=ErrorCode.VALIDATION_ERROR,
                        message=f"Question too long (max {self._settings.validation.max_question_length} chars)",
                    ),
                )

            # 获取执行器
            executor = self._executor_manager.get_executor(database)

            # 获取 Schema（带缓存）
            schema = await self._get_schema(database)

            # 生成 SQL（带重试）
            sql = await self._generate_sql_with_retry(question, schema)

            if return_type == "sql":
                return QueryResponse(
                    success=True,
                    sql=sql,
                )

            # 验证 SQL
            validation = await self._validator.validate(sql)
            if not validation.is_valid:
                return QueryResponse(
                    success=False,
                    error=ErrorDetail(
                        code=ErrorCode.SECURITY_VIOLATION,
                        message=validation.error_message or "SQL validation failed",
                    ),
                    sql=sql,
                )

            # 执行查询（带重试和断路器）
            result = await self._execute_with_resilience(executor, sql)

            return QueryResponse(
                success=True,
                data=result,
                sql=sql,
            )

        except RetryExhaustedError as e:
            return QueryResponse(
                success=False,
                error=ErrorDetail(
                    code=ErrorCode.LLM_UNAVAILABLE,
                    message=f"Service unavailable after {e.attempts} attempts",
                ),
            )
        except Exception as e:
            logger.exception("query_failed", error=str(e))
            return QueryResponse(
                success=False,
                error=ErrorDetail(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Internal error occurred",
                ),
            )

    async def _execute_with_resilience(
        self,
        executor: SQLExecutor,
        sql: str,
    ) -> QueryResult:
        """
        带韧性保护的执行（断路器 + 重试）
        """
        async def _execute():
            # 应用速率限制
            await self._rate_limiter.acquire("database")

            # 通过断路器执行
            return await self._circuit_breaker.call(
                lambda: executor.execute(sql)
            )

        # 应用重试
        retry_wrapper = with_retry(self._db_retry_config)
        return await retry_wrapper(_execute)()
```

##### 测试方案

```python
# tests/unit/test_retry.py

import pytest
import asyncio
from src.pg_mcp.resilience.retry import (
    RetryConfig,
    with_retry,
    retry_async,
    RetryExhaustedError,
)

class TestRetryConfig:
    """重试配置测试"""

    def test_calculate_delay_exponential_backoff(self):
        """测试指数退避延迟计算"""
        config = RetryConfig(
            initial_delay=1.0,
            backoff_factor=2.0,
            max_delay=10.0,
        )

        assert config.calculate_delay(0) == 1.0   # 2^0 = 1
        assert config.calculate_delay(1) == 2.0   # 2^1 = 2
        assert config.calculate_delay(2) == 4.0   # 2^2 = 4
        assert config.calculate_delay(3) == 8.0   # 2^3 = 8
        assert config.calculate_delay(4) == 10.0  # 2^4 = 16, capped at max_delay

    def test_calculate_delay_respects_max(self):
        """测试延迟不超过最大值"""
        config = RetryConfig(
            initial_delay=5.0,
            backoff_factor=3.0,
            max_delay=20.0,
        )

        # 5 * 3^5 = 1215, should be capped at 20
        assert config.calculate_delay(5) == 20.0


class TestRetryDecorator:
    """重试装饰器测试"""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt(self):
        """测试首次尝试成功"""
        call_count = 0

        @with_retry(RetryConfig(max_attempts=3))
        async def func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await func()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_succeeds_after_retry(self):
        """测试重试后成功"""
        call_count = 0

        @with_retry(RetryConfig(
            max_attempts=3,
            initial_delay=0.01,  # 快速测试
        ))
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Transient error")
            return "success"

        result = await func()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhausts_retries(self):
        """测试重试耗尽"""
        call_count = 0

        @with_retry(RetryConfig(
            max_attempts=3,
            initial_delay=0.01,
        ))
        async def func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent error")

        with pytest.raises(RetryExhaustedError) as exc_info:
            await func()

        assert exc_info.value.attempts == 3
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_only_retries_specified_exceptions(self):
        """测试只重试指定的异常"""

        @with_retry(RetryConfig(
            max_attempts=3,
            retriable_exceptions=(ValueError,),
        ))
        async def func():
            raise TypeError("Non-retriable error")

        # TypeError 不应被重试
        with pytest.raises(TypeError):
            await func()


class TestRetryAsync:
    """函数式重试测试"""

    @pytest.mark.asyncio
    async def test_retry_async_function(self):
        """测试函数式重试"""
        call_count = 0

        async def func(x: int) -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Error")
            return x * 2

        result = await retry_async(
            func,
            RetryConfig(max_attempts=3, initial_delay=0.01),
            5,
        )

        assert result == 10
        assert call_count == 2
```

---

### MC-3：可观测性集成

#### 背景

**设计规范要求**：
- 指标收集（Prometheus）
- 分布式追踪
- 健康检查端点

**当前实现**：
- 可观测性模块存在但未使用
- 无健康检查端点
- 指标未在请求路径中收集

#### 设计方案

##### 指标收集集成

```python
# src/pg_mcp/observability/metrics.py

from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from typing import Dict
import time

# 查询指标
query_total = Counter(
    "pg_mcp_query_total",
    "查询总数",
    ["database", "status"],  # status: success, error, validation_failed
)

query_duration_seconds = Histogram(
    "pg_mcp_query_duration_seconds",
    "查询执行时间（秒）",
    ["database", "phase"],  # phase: sql_generation, sql_execution, validation
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

# LLM 指标
llm_requests_total = Counter(
    "pg_mcp_llm_requests_total",
    "LLM 请求总数",
    ["operation", "status"],  # operation: sql_generation, result_validation
)

llm_tokens_used_total = Counter(
    "pg_mcp_llm_tokens_used_total",
    "LLM token 使用总数",
    ["operation"],
)

# 数据库连接池指标
db_pool_size = Gauge(
    "pg_mcp_db_pool_size",
    "数据库连接池大小",
    ["database", "state"],  # state: active, idle
)

# 韧性指标
circuit_breaker_state = Gauge(
    "pg_mcp_circuit_breaker_state",
    "断路器状态 (0=closed, 1=open, 2=half_open)",
    ["service"],
)

rate_limiter_tokens = Gauge(
    "pg_mcp_rate_limiter_tokens",
    "速率限制器可用 token 数",
    ["resource"],
)


class MetricsCollector:
    """指标收集器"""

    @staticmethod
    def record_query(database: str, status: str):
        """记录查询"""
        query_total.labels(database=database, status=status).inc()

    @staticmethod
    def record_query_duration(database: str, phase: str, duration: float):
        """记录查询执行时间"""
        query_duration_seconds.labels(database=database, phase=phase).observe(duration)

    @staticmethod
    def record_llm_request(operation: str, status: str):
        """记录 LLM 请求"""
        llm_requests_total.labels(operation=operation, status=status).inc()

    @staticmethod
    def record_llm_tokens(operation: str, tokens: int):
        """记录 LLM token 使用"""
        llm_tokens_used_total.labels(operation=operation).inc(tokens)

    @staticmethod
    def update_pool_metrics(database: str, active: int, idle: int):
        """更新连接池指标"""
        db_pool_size.labels(database=database, state="active").set(active)
        db_pool_size.labels(database=database, state="idle").set(idle)

    @staticmethod
    def export_metrics() -> bytes:
        """导出 Prometheus 指标"""
        return generate_latest(REGISTRY)


# 全局指标收集器实例
metrics = MetricsCollector()
```

##### 追踪集成

```python
# src/pg_mcp/observability/tracing.py

import uuid
import contextvars
from typing import Any
import structlog

# 请求 ID 上下文变量
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id",
    default="",
)

logger = structlog.get_logger()


def generate_request_id() -> str:
    """生成唯一请求 ID"""
    return str(uuid.uuid4())


def get_request_id() -> str:
    """获取当前请求 ID"""
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    """设置当前请求 ID"""
    request_id_var.set(request_id)


class TraceContext:
    """追踪上下文"""

    def __init__(self, operation: str, **attributes: Any):
        """
        初始化追踪上下文

        Args:
            operation: 操作名称
            **attributes: 追踪属性
        """
        self.request_id = get_request_id() or generate_request_id()
        self.operation = operation
        self.attributes = attributes
        self.start_time = 0.0

    def __enter__(self):
        """进入上下文"""
        self.start_time = time.time()
        set_request_id(self.request_id)

        logger.info(
            "trace_start",
            request_id=self.request_id,
            operation=self.operation,
            **self.attributes,
        )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        duration = time.time() - self.start_time

        if exc_type is None:
            logger.info(
                "trace_end",
                request_id=self.request_id,
                operation=self.operation,
                duration=duration,
                **self.attributes,
            )
        else:
            logger.error(
                "trace_error",
                request_id=self.request_id,
                operation=self.operation,
                duration=duration,
                error=str(exc_val),
                **self.attributes,
            )


def trace(operation: str, **attributes: Any):
    """
    追踪装饰器

    Example:
        @trace("query_database", database="main")
        async def query(sql: str):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            with TraceContext(operation, **attributes):
                return await func(*args, **kwargs)
        return wrapper
    return decorator
```

##### 编排器中集成指标和追踪

```python
# src/pg_mcp/services/orchestrator.py

import time
from ..observability.metrics import metrics
from ..observability.tracing import TraceContext, get_request_id

class QueryOrchestrator:
    """查询编排服务（带可观测性）"""

    async def query(
        self,
        question: str,
        database: str | None = None,
        return_type: str = "result",
    ) -> QueryResponse:
        """执行查询（完整可观测性）"""
        # 创建追踪上下文
        with TraceContext("query", database=database or "default"):
            request_id = get_request_id()
            db_name = database or self._settings.default_database

            try:
                # 验证问题长度
                if len(question) > self._settings.validation.max_question_length:
                    metrics.record_query(db_name, "validation_failed")
                    return QueryResponse(
                        success=False,
                        error=ErrorDetail(
                            code=ErrorCode.VALIDATION_ERROR,
                            message=f"Question too long",
                        ),
                    )

                # 获取执行器
                executor = self._executor_manager.get_executor(database)

                # 获取 Schema
                schema = await self._get_schema(database)

                # 生成 SQL（记录时间）
                sql_gen_start = time.time()
                sql = await self._generate_sql_with_retry(question, schema)
                sql_gen_duration = time.time() - sql_gen_start

                metrics.record_query_duration(db_name, "sql_generation", sql_gen_duration)
                metrics.record_llm_request("sql_generation", "success")

                if return_type == "sql":
                    metrics.record_query(db_name, "success")
                    return QueryResponse(
                        success=True,
                        sql=sql,
                    )

                # 验证 SQL
                validation = await self._validator.validate(sql)
                if not validation.is_valid:
                    metrics.record_query(db_name, "validation_failed")
                    return QueryResponse(
                        success=False,
                        error=ErrorDetail(
                            code=ErrorCode.SECURITY_VIOLATION,
                            message=validation.error_message or "SQL validation failed",
                        ),
                        sql=sql,
                    )

                # 执行查询（记录时间）
                exec_start = time.time()
                result = await self._execute_with_resilience(executor, sql)
                exec_duration = time.time() - exec_start

                metrics.record_query_duration(db_name, "sql_execution", exec_duration)
                metrics.record_query(db_name, "success")

                return QueryResponse(
                    success=True,
                    data=result,
                    sql=sql,
                )

            except Exception as e:
                metrics.record_query(db_name, "error")
                logger.exception("query_failed", request_id=request_id, error=str(e))

                return QueryResponse(
                    success=False,
                    error=ErrorDetail(
                        code=ErrorCode.INTERNAL_ERROR,
                        message="Internal error occurred",
                    ),
                )
```

##### 健康检查端点

```python
# src/pg_mcp/server.py

from fastapi import FastAPI, Response
from fastmcp import FastMCP
from .observability.metrics import metrics

# 创建 FastAPI 应用（用于健康检查和指标）
api = FastAPI(title="PG-MCP Health and Metrics")

@api.get("/health")
async def health_check() -> dict:
    """
    健康检查端点

    Returns:
        健康状态
    """
    # 检查数据库连接
    try:
        # 简单的连接检查
        for db_name, pool in _pools.items():
            if pool.get_size() == 0:
                return {
                    "status": "unhealthy",
                    "reason": f"Database '{db_name}' pool has no connections",
                }

        return {
            "status": "healthy",
            "databases": list(_pools.keys()),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "reason": str(e),
        }


@api.get("/health/ready")
async def readiness_check() -> dict:
    """
    就绪检查端点

    检查服务是否准备好接受请求
    """
    if _orchestrator is None:
        return {
            "status": "not_ready",
            "reason": "Service not initialized",
        }

    return {
        "status": "ready",
    }


@api.get("/health/live")
async def liveness_check() -> dict:
    """
    存活检查端点

    检查服务是否仍在运行
    """
    return {
        "status": "alive",
    }


@api.get("/metrics")
async def prometheus_metrics() -> Response:
    """
    Prometheus 指标端点

    Returns:
        Prometheus 格式的指标
    """
    metrics_data = metrics.export_metrics()
    return Response(
        content=metrics_data,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
```

##### 测试方案

```python
# tests/unit/test_observability.py

import pytest
from prometheus_client import REGISTRY
from src.pg_mcp.observability.metrics import metrics, query_total
from src.pg_mcp.observability.tracing import TraceContext, get_request_id

class TestMetrics:
    """指标收集测试"""

    def test_record_query_increments_counter(self):
        """测试记录查询增加计数器"""
        before = query_total.labels(database="test", status="success")._value.get()

        metrics.record_query("test", "success")

        after = query_total.labels(database="test", status="success")._value.get()
        assert after == before + 1

    def test_export_metrics_returns_bytes(self):
        """测试导出指标返回字节"""
        data = metrics.export_metrics()

        assert isinstance(data, bytes)
        assert b"pg_mcp_query_total" in data


class TestTracing:
    """追踪测试"""

    def test_trace_context_sets_request_id(self):
        """测试追踪上下文设置请求 ID"""
        with TraceContext("test_operation") as ctx:
            request_id = get_request_id()

            assert request_id == ctx.request_id
            assert len(request_id) > 0

    def test_trace_context_logs_operation(self, caplog):
        """测试追踪上下文记录操作"""
        with TraceContext("test_operation", foo="bar"):
            pass

        assert "trace_start" in caplog.text
        assert "test_operation" in caplog.text
        assert "trace_end" in caplog.text
```

---

### MC-4：测试基础设施完善

#### 背景

**问题**：
- 集成/端到端测试依赖真实外部服务
- 没有 mock 支持
- 测试不确定性

#### 设计方案

##### Mock OpenAI 客户端

```python
# tests/mocks/openai_mock.py

from typing import Any, Dict, List
from unittest.mock import AsyncMock

class MockOpenAIClient:
    """Mock OpenAI 客户端"""

    def __init__(self):
        self.chat = MockChatCompletion()
        self.responses: Dict[str, str] = {}
        self.call_count = 0

    def set_response(self, prompt_key: str, response: str):
        """设置预定义响应"""
        self.responses[prompt_key] = response

    def get_call_count(self) -> int:
        """获取调用次数"""
        return self.call_count


class MockChatCompletion:
    """Mock Chat Completion API"""

    def __init__(self):
        self.completions = MockCompletions()


class MockCompletions:
    """Mock Completions"""

    def __init__(self):
        self._responses = {}
        self._call_count = 0

    async def create(self, **kwargs: Any) -> MockChatResponse:
        """创建 completion（mock）"""
        self._call_count += 1

        messages = kwargs.get("messages", [])
        user_message = next(
            (m["content"] for m in messages if m["role"] == "user"),
            ""
        )

        # 根据关键词匹配响应
        response_text = "SELECT * FROM users"  # 默认响应

        if "count" in user_message.lower():
            response_text = "SELECT COUNT(*) FROM users"
        elif "analytics" in user_message.lower():
            response_text = "SELECT date, SUM(amount) FROM orders GROUP BY date"

        return MockChatResponse(
            choices=[
                MockChoice(
                    message=MockMessage(content=response_text),
                    finish_reason="stop",
                )
            ],
            usage=MockUsage(total_tokens=100),
        )


class MockChatResponse:
    """Mock Chat Response"""

    def __init__(self, choices: List, usage: Any):
        self.choices = choices
        self.usage = usage


class MockChoice:
    """Mock Choice"""

    def __init__(self, message: Any, finish_reason: str):
        self.message = message
        self.finish_reason = finish_reason


class MockMessage:
    """Mock Message"""

    def __init__(self, content: str):
        self.content = content


class MockUsage:
    """Mock Usage"""

    def __init__(self, total_tokens: int):
        self.total_tokens = total_tokens
```

##### Mock PostgreSQL 连接

```python
# tests/mocks/postgres_mock.py

from typing import List, Dict, Any
from unittest.mock import AsyncMock

class MockPostgresPool:
    """Mock PostgreSQL 连接池"""

    def __init__(self):
        self._closed = False
        self._query_results: Dict[str, List[Dict[str, Any]]] = {}

    def set_query_result(self, sql_pattern: str, result: List[Dict[str, Any]]):
        """设置查询结果"""
        self._query_results[sql_pattern] = result

    async def fetch(self, sql: str, *args) -> List[Dict[str, Any]]:
        """执行查询（mock）"""
        if self._closed:
            raise RuntimeError("Pool is closed")

        # 匹配 SQL 模式
        for pattern, result in self._query_results.items():
            if pattern in sql:
                return result

        # 默认空结果
        return []

    async def close(self):
        """关闭连接池"""
        self._closed = True

    def get_size(self) -> int:
        """获取连接池大小"""
        return 10 if not self._closed else 0


class MockPostgresConnection:
    """Mock PostgreSQL 连接"""

    def __init__(self, pool: MockPostgresPool):
        self._pool = pool

    async def fetch(self, sql: str, *args) -> List[Dict[str, Any]]:
        """执行查询"""
        return await self._pool.fetch(sql, *args)
```

##### 集成测试 Fixtures

```python
# tests/conftest.py

import pytest
from tests.mocks.openai_mock import MockOpenAIClient
from tests.mocks.postgres_mock import MockPostgresPool
from src.pg_mcp.config.settings import Settings, DatabaseConfig

@pytest.fixture
def mock_openai():
    """Mock OpenAI 客户端 fixture"""
    return MockOpenAIClient()

@pytest.fixture
def mock_postgres_pool():
    """Mock PostgreSQL 连接池 fixture"""
    pool = MockPostgresPool()

    # 设置常见查询结果
    pool.set_query_result(
        "SELECT * FROM users",
        [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
    )

    pool.set_query_result(
        "SELECT COUNT(*) FROM users",
        [{"count": 2}]
    )

    return pool

@pytest.fixture
def test_settings():
    """测试配置 fixture"""
    return Settings(
        databases=[
            DatabaseConfig(
                name="test",
                host="localhost",
                port=5432,
                database="test_db",
                user="test_user",
                password="test_pass",
            )
        ],
        default_database="test",
    )
```

##### 确定性集成测试

```python
# tests/integration/test_full_flow_mock.py

import pytest
from src.pg_mcp.services.orchestrator import QueryOrchestrator
from src.pg_mcp.services.sql_executor import ExecutorManager, SQLExecutor

@pytest.mark.asyncio
async def test_query_flow_with_mocks(
    mock_openai,
    mock_postgres_pool,
    test_settings,
):
    """测试完整查询流程（使用 mock）"""
    # 设置 mock 响应
    mock_openai.set_response(
        "generate_sql",
        "SELECT COUNT(*) FROM users"
    )

    # 创建执行器
    executor = SQLExecutor(
        pool=mock_postgres_pool,
        security_config=test_settings.security,
        database_name="test",
    )

    executor_manager = ExecutorManager(
        executors={"test": executor},
        default_database="test",
    )

    # 创建编排器
    orchestrator = QueryOrchestrator(
        settings=test_settings,
        executor_manager=executor_manager,
        circuit_breaker=mock_circuit_breaker,
        rate_limiter=mock_rate_limiter,
    )

    # 执行查询
    response = await orchestrator.query("How many users are there?")

    # 验证结果
    assert response.success
    assert response.data is not None
    assert response.data.row_count == 1
    assert response.sql == "SELECT COUNT(*) FROM users"
```

---

## 架构合规性改进

### AC-1：安全配置增强

#### 当前问题

- `SecurityConfig` 缺少 `blocked_tables`、`blocked_columns`、`allow_explain` 字段
- 验证器无法强制执行敏感资源保护

#### 解决方案

```python
# src/pg_mcp/config/settings.py

class SecurityConfig(BaseModel):
    """安全配置"""

    # 现有字段
    allow_write: bool = Field(False, description="是否允许写操作")
    allow_drop: bool = Field(False, description="是否允许 DROP 操作")
    blocked_functions: list[str] = Field(
        default_factory=lambda: [
            "pg_sleep",
            "pg_read_file",
            "pg_ls_dir",
            "pg_terminate_backend",
        ],
        description="阻止的函数列表",
    )

    # 新增字段
    blocked_tables: list[str] = Field(
        default_factory=list,
        description="阻止访问的表名列表（支持通配符）",
    )

    blocked_columns: Dict[str, list[str]] = Field(
        default_factory=dict,
        description="阻止访问的列（表名 -> 列名列表）",
    )

    allow_explain: bool = Field(
        True,
        description="是否允许 EXPLAIN 语句",
    )

    require_where_clause: list[str] = Field(
        default_factory=list,
        description="要求必须有 WHERE 子句的表列表",
    )

    max_join_tables: int = Field(
        10,
        ge=1,
        le=50,
        description="最大 JOIN 表数量",
    )


# 环境变量配置示例
# SECURITY__BLOCKED_TABLES='["users_sensitive", "audit_logs", "credentials"]'
# SECURITY__BLOCKED_COLUMNS='{"users": ["password_hash", "ssn"], "orders": ["credit_card"]}'
# SECURITY__ALLOW_EXPLAIN=true
```

集成到验证器：

```python
# src/pg_mcp/services/sql_validator.py

class SQLValidator:
    """SQL 安全验证器"""

    def __init__(self, security_config: SecurityConfig):
        self._config = security_config

    def validate(self, sql: str) -> ValidationResult:
        """验证 SQL 安全性"""
        try:
            # 解析 SQL
            statements = sqlglot.parse(sql)

            for stmt in statements:
                # 检查阻止的表
                if self._config.blocked_tables:
                    tables = self._extract_tables(stmt)
                    for table in tables:
                        if self._is_blocked_table(table):
                            return ValidationResult(
                                is_valid=False,
                                error_message=f"Access to table '{table}' is blocked",
                            )

                # 检查阻止的列
                if self._config.blocked_columns:
                    columns = self._extract_columns(stmt)
                    for table, column in columns:
                        if self._is_blocked_column(table, column):
                            return ValidationResult(
                                is_valid=False,
                                error_message=f"Access to column '{table}.{column}' is blocked",
                            )

                # 检查 EXPLAIN
                if not self._config.allow_explain and self._is_explain(stmt):
                    return ValidationResult(
                        is_valid=False,
                        error_message="EXPLAIN statements are not allowed",
                    )

                # 检查 WHERE 子句要求
                if self._config.require_where_clause:
                    if not self._has_where_clause(stmt):
                        tables = self._extract_tables(stmt)
                        for table in tables:
                            if table in self._config.require_where_clause:
                                return ValidationResult(
                                    is_valid=False,
                                    error_message=f"WHERE clause required for table '{table}'",
                                )

            return ValidationResult(is_valid=True)

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"SQL parsing failed: {e}",
            )

    def _is_blocked_table(self, table: str) -> bool:
        """检查表是否被阻止"""
        for pattern in self._config.blocked_tables:
            if fnmatch.fnmatch(table.lower(), pattern.lower()):
                return True
        return False

    def _is_blocked_column(self, table: str, column: str) -> bool:
        """检查列是否被阻止"""
        if table in self._config.blocked_columns:
            blocked_cols = self._config.blocked_columns[table]
            return column.lower() in [c.lower() for c in blocked_cols]
        return False
```

---

### AC-2：速率限制集成

#### 解决方案

在编排器中应用速率限制（已在 MC-2 中实现）：

```python
# src/pg_mcp/services/orchestrator.py

async def _execute_with_resilience(
    self,
    executor: SQLExecutor,
    sql: str,
) -> QueryResult:
    """带韧性保护的执行"""
    # 应用速率限制
    await self._rate_limiter.acquire("database")

    # 应用速率限制（LLM）
    await self._rate_limiter.acquire("llm")

    # 通过断路器执行
    return await self._circuit_breaker.call(
        lambda: executor.execute(sql)
    )
```

---

### AC-3：输入验证强化

#### 解决方案

在编排器中强制执行验证配置（已在 MC-2 中实现）：

```python
# 在 query() 方法开始时
if len(question) > self._settings.validation.max_question_length:
    return QueryResponse(
        success=False,
        error=ErrorDetail(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Question too long (max {self._settings.validation.max_question_length} chars)",
        ),
    )
```

---

### AC-4：置信度阈值应用

#### 解决方案

```python
# src/pg_mcp/services/orchestrator.py

async def query(self, question: str, ...) -> QueryResponse:
    """执行查询（应用置信度阈值）"""
    # ... 执行查询 ...

    # 验证结果
    validation = await self._result_validator.validate(
        question=question,
        sql=sql,
        result=result,
    )

    # 应用置信度阈值
    min_confidence = self._settings.validation.min_confidence_score
    if validation.confidence < min_confidence:
        return QueryResponse(
            success=False,
            error=ErrorDetail(
                code=ErrorCode.LOW_CONFIDENCE,
                message=f"Result confidence {validation.confidence} below threshold {min_confidence}",
                details={"confidence": validation.confidence, "threshold": min_confidence},
            ),
            sql=sql,
            confidence=validation.confidence,
        )

    return QueryResponse(
        success=True,
        data=result,
        sql=sql,
        confidence=validation.confidence,
    )
```

---

## 实施计划

### 阶段 1：代码质量修复（1-2 天）

**任务**：
- [ ] CQ-1: 删除 `QueryResponse.to_dict()` 重复定义
- [ ] CQ-2: 统一 `ErrorDetail` 类定义
- [ ] CQ-3: 修复冗余断路器实例化
- [ ] CQ-4: 标记未使用配置字段（留待阶段 2 实现）

**验收标准**：
- 所有代码质量 lint 检查通过
- 单元测试覆盖所有修复

### 阶段 2：多数据库支持（3-5 天）

**任务**：
- [ ] MC-1.1: 更新配置模型支持多数据库
- [ ] MC-1.2: 实现 `create_pools()` 和 `ExecutorManager`
- [ ] MC-1.3: 更新编排器使用执行器管理器
- [ ] MC-1.4: 添加多数据库集成测试

**验收标准**：
- 支持配置多个数据库
- 可以正确路由到不同数据库
- 集成测试覆盖多数据库场景

### 阶段 3：韧性层完善（2-3 天）

**任务**：
- [ ] MC-2.1: 实现 `resilience/retry.py` 模块
- [ ] MC-2.2: 在编排器中集成重试逻辑
- [ ] MC-2.3: 添加重试单元测试
- [ ] MC-2.4: 集成断路器和速率限制器

**验收标准**：
- 瞬态故障自动重试
- 重试配置生效
- 断路器和速率限制器在请求路径中应用

### 阶段 4：可观测性集成（2-3 天）

**任务**：
- [ ] MC-3.1: 在编排器中集成指标收集
- [ ] MC-3.2: 实现追踪上下文传播
- [ ] MC-3.3: 添加健康检查端点
- [ ] MC-3.4: 添加 Prometheus 指标端点

**验收标准**：
- 指标正确收集并可导出
- 请求 ID 在日志中传播
- 健康检查端点工作正常

### 阶段 5：安全增强（1-2 天）

**任务**：
- [ ] AC-1: 扩展 `SecurityConfig` 字段
- [ ] AC-2: 更新验证器支持新配置
- [ ] AC-3: 强制执行输入长度验证
- [ ] AC-4: 应用置信度阈值

**验收标准**：
- 所有安全配置生效
- 安全测试覆盖新功能

### 阶段 6：测试基础设施（3-4 天）

**任务**：
- [ ] MC-4.1: 实现 OpenAI mock 客户端
- [ ] MC-4.2: 实现 PostgreSQL mock 连接
- [ ] MC-4.3: 重写集成测试使用 mock
- [ ] MC-4.4: 添加确定性端到端测试

**验收标准**：
- 所有测试可以离线运行
- 测试结果确定性
- CI 集成无外部依赖

### 总计时间估算

- **最少**: 12 天
- **最多**: 19 天
- **推荐**: 15 天（3 周冲刺）

---

## 验收标准

### 代码质量

- [ ] Ruff lint 无错误
- [ ] MyPy 类型检查无错误
- [ ] 无重复代码
- [ ] 无未使用的配置字段（或已实现使用）

### 功能完整性

- [ ] 多数据库支持工作正常
- [ ] 重试/退避机制生效
- [ ] 速率限制应用于 LLM 和数据库
- [ ] 断路器保护关键路径
- [ ] 安全配置完整且生效

### 可观测性

- [ ] 指标正确收集
- [ ] 请求 ID 传播
- [ ] 健康检查端点可用
- [ ] Prometheus 端点可用

### 测试

- [ ] 单元测试覆盖率 >= 80%
- [ ] 安全模块覆盖率 >= 95%
- [ ] 集成测试使用 mock
- [ ] 所有测试可离线运行
- [ ] CI 集成成功

### 文档

- [ ] 所有新模块有 docstring
- [ ] 配置字段有说明
- [ ] README 更新
- [ ] 环境配置示例完整

---

## 风险评估

### 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 多数据库路由复杂性 | 中 | 高 | 详细设计和充分测试 |
| Mock 不完整导致测试失败 | 中 | 中 | 逐步迁移，保留原有测试 |
| 性能回退 | 低 | 中 | 添加性能测试基准 |

### 进度风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 时间估算不足 | 中 | 中 | 分阶段交付，优先 P1 |
| 资源不足 | 低 | 高 | 提前规划资源分配 |

---

## 附录

### A. 配置示例

```toml
# pyproject.toml

[project]
name = "pg-mcp"
version = "0.3.0"  # 版本升级
```

```bash
# .env.example

# 多数据库配置
DATABASES='[
  {"name": "main", "host": "localhost", "port": 5432, ...},
  {"name": "analytics", "host": "analytics.db", ...}
]'
DEFAULT_DATABASE=main

# 安全配置
SECURITY__BLOCKED_TABLES='["users_sensitive", "audit_*"]'
SECURITY__BLOCKED_COLUMNS='{"users": ["password", "ssn"]}'
SECURITY__ALLOW_EXPLAIN=true

# 韧性配置
RESILIENCE__MAX_RETRIES=3
RESILIENCE__RETRY_DELAY=1.0
RESILIENCE__BACKOFF_FACTOR=2.0

# 验证配置
VALIDATION__MAX_QUESTION_LENGTH=10000
VALIDATION__MIN_CONFIDENCE_SCORE=70
```

### B. 测试命令

```bash
# 运行所有测试（带覆盖率）
pytest --cov=src --cov-report=html --cov-report=term

# 只运行单元测试
pytest tests/unit/

# 只运行集成测试（使用 mock）
pytest tests/integration/ -m "not requires_db"

# 类型检查
mypy src

# Lint
ruff check src tests
```

---

## 修订历史

| 版本 | 日期 | 作者 | 修改内容 |
|------|------|------|----------|
| v1.0 | 2026-02-05 | 开发团队 | 初始版本 |
