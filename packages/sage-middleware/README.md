# SAGE Middleware（中间件）

> 用于构建带有 AI 能力的流式数据应用的中间件层

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](../../LICENSE)
[![PyPI](https://img.shields.io/pypi/v/isage-middleware.svg)](https://pypi.org/project/isage-middleware/)

## 📋 Overview

SAGE Middleware 是 SAGE 框架的 L4 中间件层，提供高性能的数据处理组件和 AI
能力集成。它集成了多家大模型提供商、异步任务调度、安全鉴权以及核心数据处理组件（向量数据库、流处理引擎等）。

## 🧭 Governance / 团队协作制度

- `docs/governance/TEAM.md`
- `docs/governance/MAINTAINERS.md`
- `docs/governance/DEVELOPER_GUIDE.md`
- `docs/governance/PR_CHECKLIST.md`
- `docs/governance/SELF_HOSTED_RUNNER.md`
- `docs/governance/TODO.md`

## ✨ Key Features

- 🤖 **LLM 推理**：
  - **sageLLM** ✅ 推荐：统一 LLM 推理引擎，支持 CUDA/Ascend/Mock 后端
  - vLLM ⚠️ 已弃用：将在 v0.4.0 移除，请迁移至 sageLLM
- 🔎 检索与向量：RAG、BM25、FAISS 等
- 📋 任务调度：Celery 异步任务
- 🔐 安全鉴权：JWT、密码学工具
- ⚙️ 核心组件：
  - `sage_db`：数据库/向量存储相关组件（含 C/C++ 扩展）
  - `sage_flow`：高性能向量流处理（可能包含扩展或独立子模块）

## 🚀 Installation

### Basic Installation

```bash
pip install isage-middleware
```

### Development Installation

```bash
git clone https://github.com/intellistream/SAGE.git
cd SAGE/packages/sage-middleware
pip install -e .
```

> 说明：中间件组件（sage_db/sage_flow/sage_tsdb 等）现已随源码直接提供或通过 pip 依赖分发，无需初始化任何子模块。

### With Optional Dependencies

```bash
# 可选：VLLM 支持（需要 CUDA）
pip install isage-common[vllm]

# 可选：与完整 SAGE 框架集成
pip install isage-middleware[sage]
```

## 📖 Quick Start

### LLM 推理（推荐：sageLLM）

```python
from sage.middleware.operators.llm import SageLLMGenerator

# 自动选择最佳后端
generator = SageLLMGenerator(
    model_path="Qwen/Qwen2.5-7B-Instruct",
    backend_type="auto",  # auto/cuda/ascend/mock
    temperature=0.7,
    max_tokens=2048,
)

result = generator.execute("你好，世界！")
print(result)
```

### API 客户端

```python
from sage.middleware.api.client import APIClient
from sage.middleware.auth.jwt import JWTManager

client = APIClient()
jwt_manager = JWTManager()

resp = client.chat_completion(
    provider="openai",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(resp)
```

> 📖 **迁移指南**：如果您正在使用 `VLLMGenerator`，请参阅 [Project Changelog](../../CHANGELOG.md)

## 📦 Package Structure

```
sage-middleware/
├── src/
│   └── sage/
│       └── middleware/
│           ├── __init__.py
│           ├── operators/          # Dataflow operators
│           │   ├── llm/           # LLM operators (sageLLM)
│           │   ├── rag/           # RAG operators
│           │   └── agentic/       # Agent operators
│           ├── components/         # Core components
│           │   ├── sage_db/       # Vector database (C++ extensions)
│           │   ├── sage_flow/     # Stream processing (C++ extensions)
│           │   ├── sage_tsdb/     # Time-series DB (C++ extensions)
│           │   ├── sage_mem/      # Memory management
│           │   └── sage_refiner/  # Context compression
│           ├── api/                # API clients
│           └── auth/               # Authentication
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
│   └── governance/                # Team collaboration
├── README.md
├── pyproject.toml
└── setup.py
```

## 🔧 Configuration

配置可以通过以下方式提供：

- 环境变量
- YAML/TOML 配置文件
- 直接通过 API 参数

### 配置示例

```yaml
# config.yaml
middleware:
  auth:
    secret_key: "your-secret-key"  # pragma: allowlist secret
    algorithm: "HS256"
  providers:
    openai:
      api_key: "sk-..."  # pragma: allowlist secret
      base_url: "https://api.openai.com/v1"
```

## 📚 Documentation

- **用户指南**: 参见 [SAGE-Pub](https://intellistream.github.io/SAGE-Pub/)
- **API 参考**: 参见 [API 文档](https://intellistream.github.io/SAGE-Pub/api/)
- **治理文档**: 参见 [docs/governance/](docs/governance/)
- **迁移指南**: 参见 [Project Changelog](../../CHANGELOG.md)

## 🧪 Testing

```bash
# 运行单元测试
pytest tests/unit -v

# 运行集成测试
pytest tests/integration -v

# 运行所有测试并生成覆盖率报告
pytest --cov=sage.middleware --cov-report=html
```

## 🤝 Contributing

欢迎贡献！请参阅：

- **贡献指南**: [CONTRIBUTING.md](../../CONTRIBUTING.md)
- **开发者文档**: [DEVELOPER.md](../../DEVELOPER.md)
- **PR 检查清单**: [docs/governance/PR_CHECKLIST.md](docs/governance/PR_CHECKLIST.md)

### 新增中间件组件规范

当添加新的中间件组件时，请遵循以下要求：

1. **目录结构**: 在 `src/sage/middleware/components/` 下创建组件目录
1. **C++ 扩展**: 如包含 C++ 扩展，必须遵守依赖约束（参见下文详细规范）
1. **构建脚本**: 提供标准的 `build.sh`，支持 `--install-deps`
1. **setup.py 集成**: 在 `setup.py` 中添加构建方法
1. **测试**: 添加单元测试和集成测试
1. **文档**: 更新 README 和相关文档

## 📄 License

本项目采用 MIT License - 详见 [LICENSE](../../LICENSE) 文件

## 🔗 Related Packages

- **sage-kernel**: 核心计算引擎（L3）
- **sage-common**: 通用工具（L1）
- **sage-libs**: 可复用算法库（L3）
- **sage-platform**: 平台服务（L2）
- **isage-vdb**: 向量数据库（独立包）
- **isage-neuromem**: 内存管理系统（独立包）
- **isage-refiner**: 上下文压缩（独立包）

## 📮 Support

- **文档**: https://intellistream.github.io/SAGE-Pub/
- **问题反馈**: https://github.com/intellistream/SAGE/issues
- **讨论**: https://github.com/intellistream/SAGE/discussions

______________________________________________________________________

**Part of the SAGE Framework** | [主仓库](https://github.com/intellistream/SAGE)
