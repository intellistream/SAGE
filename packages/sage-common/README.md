# SAGE Common

> SAGE 框架的核心工具和共享组件

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](../../LICENSE)

## 📋 Overview

**SAGE Common** 提供所有 SAGE 包共用的基础工具和组件。 这是基础层（L1），提供：

## 🧭 Governance / 团队协作制度

- `docs/governance/TEAM.md`

- `docs/governance/MAINTAINERS.md`

- `docs/governance/DEVELOPER_GUIDE.md`

- `docs/governance/PR_CHECKLIST.md`

- `docs/governance/SELF_HOSTED_RUNNER.md`

- `docs/governance/TODO.md`

- **配置管理** - YAML/TOML 文件支持

- **日志框架** - 自定义格式化器和处理程序

- **网络工具** - TCP/UDP 通信支持

- **序列化工具** - dill 和 pickle 支持

- **系统工具** - 环境和进程管理

- **嵌入服务** - sage_embedding、sage_llm

该包确保 SAGE 生态系统的一致性并减少代码重复。

## ✨ Features

- **统一配置** - YAML/TOML 配置加载和验证
- **高级日志** - 彩色输出、结构化日志、自定义格式器
- **网络工具** - TCP 客户端/服务器、网络助手
- **灵活序列化** - 多种后端（dill、pickle、JSON）
- **系统管理** - 环境检测、进程控制
- **LLM 集成** - 嵌入和 vLLM 服务

## 🚀 Quick Start

### 配置管理

```python
from sage.common.utils.config import load_config

# 加载 YAML 配置
config = load_config("config.yaml")
print(config["database"]["host"])
```

### 日志记录

```python
from sage.common.utils.logging import get_logger

logger = get_logger(__name__)
logger.info("Processing started")
logger.error("An error occurred", extra={"user_id": 123})
```

### 序列化

```python
from sage.common.utils.serialization import UniversalSerializer

serializer = UniversalSerializer()
data = {"key": "value", "nested": {"data": [1, 2, 3]}}
serialized = serializer.serialize(data)
deserialized = serializer.deserialize(serialized)
```

## 核心模块

- **utils.config** - 配置管理工具
- **utils.logging** - 日志框架和格式化器
- **utils.network** - 网络工具和 TCP 客户端/服务器
- **utils.serialization** - 序列化工具（包含 dill 支持）
- **utils.system** - 环境和进程管理的系统工具
- **\_version** - 版本管理

## 📦 Package Structure

```
sage-common/
├── src/
│   └── sage/
│       └── common/
│           ├── __init__.py
│           ├── _version.py
│           ├── utils/                  # 核心工具
│           │   ├── config/            # 配置管理
│           │   ├── logging/           # 日志框架
│           │   ├── network/           # 网络工具
│           │   ├── serialization/     # 序列化工具
│           │   └── system/            # 系统工具
│           └── components/            # 共享组件
│               ├── sage_embedding/    # 嵌入服务
│               └── sage_llm/         # vLLM 服务
├── tests/
├── pyproject.toml
└── README.md
```

## 🚀 Installation

### 基础安装

```bash
pip install isage-common
```

### 开发安装

```bash
cd packages/sage-common
pip install -e .
```

### 可选依赖安装

```bash
# 嵌入支持
pip install isage-common[embedding]

# vLLM 支持
pip install isage-common[vllm]

# 完整安装
pip install isage-common[all]
```

## 📖 快速开始

### 配置管理

```python
from sage.common.utils.config.loader import ConfigLoader

# 加载配置
config = ConfigLoader("config.yaml")

# 访问配置
model_name = config.get("model.name", default="default-model")
```

### 日志

```python
from sage.common.utils.logging.custom_logger import get_logger

# 获取日志器
logger = get_logger(__name__)

# 使用日志器
logger.info("应用程序已启动")
logger.debug("调试信息")
logger.error("发生错误", exc_info=True)
```

### 网络工具

```python
from sage.common.utils.network import TCPClient, TCPServer

# 创建 TCP 服务器
server = TCPServer(host="localhost", port=8080)
server.start()

# 创建 TCP 客户端
client = TCPClient(host="localhost", port=8080)
client.connect()
client.send(b"你好，服务器！")
```

### 序列化

```python
from sage.common.utils.serialization import serialize, deserialize

# 序列化数据
data = {"key": "value", "numbers": [1, 2, 3]}
serialized = serialize(data, format="dill")

# 反序列化数据
restored = deserialize(serialized, format="dill")
```

## 🔧 Configuration

配置文件通常使用 YAML 或 TOML 格式：

```yaml
# config.yaml
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

network:
  host: localhost
  port: 8080
  timeout: 30

embedding:
  model: sentence-transformers/all-MiniLM-L6-v2
  device: cuda
```

## 🧪 Testing

```bash
# 运行单元测试
pytest tests/unit

# 运行集成测试
pytest tests/integration

# 运行覆盖率测试
pytest --cov=sage.common --cov-report=html
```

## 📚 Documentation

- **用户指南** - 查看 [docs-public](https://intellistream.github.io/SAGE-Pub/guides/packages/sage-common/)
- **API 参考** - 查看包文档字符串和类型提示
- **示例** - 查看各模块中的 `examples/` 目录

## 🤝 Contributing

欢迎贡献！请查看 [CONTRIBUTING.md](../../CONTRIBUTING.md) 了解指导原则。

## 📄 License

该项目采用 MIT 许可证 - 详情请查看 [LICENSE](../../LICENSE) 文件。

## 🔗 相关包

- **sage-kernel** - 使用通用工具进行运行时管理
- **sage-libs** - 基于通用组件构建库
- **sage-middleware** - 使用网络和序列化工具
- **sage-tools** - 使用配置和日志工具

## 📮 支持

- **文档** - https://intellistream.github.io/SAGE-Pub/
- **问题** - https://github.com/intellistream/SAGE/issues
- **讨论** - https://github.com/intellistream/SAGE/discussions

______________________________________________________________________

**SAGE 框架的一部分** | [主仓库](https://github.com/intellistream/SAGE)
