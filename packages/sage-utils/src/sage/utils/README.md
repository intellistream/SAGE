# SAGE 工具模块 (Utils)

SAGE工具模块提供框架运行所需的各种实用工具和辅助功能，是整个SAGE生态系统的基础支撑模块。

## 模块概述

工具模块包含了日志记录、配置管理、序列化、网络通信、系统操作、AI模型集成等核心功能，为SAGE的其他模块提供统一的工具服务。

## 核心子模块

### [嵌入模型集成](./embedding_methods/)
- 统一的嵌入模型API接口
- 支持多种本地和云端嵌入服务
- 包括OpenAI、Hugging Face、Ollama等主流服务
- 提供向量化和语义搜索能力

### [序列化工具](./serialization/)
- 通用对象序列化接口
- 支持复杂Python对象序列化
- 提供Dill和Universal序列化器
- 适用于分布式环境下的对象传输

### [客户端集成](./clients/)
- 外部AI服务客户端封装
- OpenAI、Hugging Face等API集成
- 统一的文本生成和推理接口
- 支持批量处理和异步调用

### [系统工具](./system/)
- 跨平台系统操作工具
- 环境管理、网络检测、进程控制
- 资源监控和性能优化
- 安全的系统交互封装

### [网络通信](./network/)
- TCP客户端和服务器实现
- 可靠的网络通信基础设施
- 支持分布式环境下的数据传输
- 包含连接管理和错误处理

### [测试框架](./tests/)
- 工具模块的完整测试覆盖
- 单元测试和集成测试
- 性能基准测试
- 持续集成支持

## 核心功能文件

### 配置和日志
- `config_loader.py` - 统一配置加载器
- `custom_logger.py` - 自定义日志系统
- `custom_formatter.py` - 日志格式化工具
- `logging_utils.py` - 日志工具函数

### 队列和通信
- `queue.py` - 队列抽象和工具
- `queue_adapter.py` - 队列适配器
- `queue_config.py` - 队列配置管理
- `queue_tool.py` - 队列操作工具
- `queue_diagnostic.py` - 队列诊断工具
- `queue_auto_fallback.py` - 队列故障转移

### Ray集成
- `ray_helper.py` - Ray分布式计算助手
- `actor_wrapper.py` - Ray Actor包装器

### 状态和数据
- `state_persistence.py` - 状态持久化工具

## 主要特性

- **模块化设计**: 功能划分清晰，可独立使用
- **统一接口**: 为相似功能提供一致的API
- **跨平台支持**: 兼容主流操作系统
- **高性能**: 优化的实现和缓存机制
- **易扩展**: 支持自定义扩展和插件
- **完善测试**: 高覆盖率的测试保障

## 使用场景

- **基础设施**: 为SAGE其他模块提供基础服务
- **AI集成**: 与各种AI模型和服务的集成
- **分布式计算**: 支持分布式环境下的协调
- **系统管理**: 自动化的系统操作和监控
- **开发调试**: 日志记录和诊断工具

## 快速开始

```python
# 配置加载
from sage.utils.config_loader import ConfigLoader
config = ConfigLoader("app_config.yaml")

# 日志记录
from sage.utils.logger.custom_logger import get_logger
logger = get_logger("my_app")
logger.info("Application started")

# AI模型调用
from sage.utils.embedding_methods import apply_embedding_model
model = apply_embedding_model("openai")
embedding = model.embed("Hello world")

# 系统工具
from sage.utils.system import NetworkUtils
net_utils = NetworkUtils()
free_port = net_utils.find_free_port()
```

## 配置管理

工具模块支持多种配置方式：
- YAML/JSON配置文件
- 环境变量覆盖
- 运行时动态配置
- 默认配置和用户配置合并

## 扩展开发

工具模块采用插件化架构，支持：
- 自定义嵌入模型提供商
- 新的序列化方式
- 额外的系统工具
- 定制化的网络协议

通过继承相应的基类即可添加新功能，详见各子模块的README文档。
