# SAGE Kernel

> 🚀 SAGE 框架的核心内核包 - 整合了核心框架和命令行工具

## 📦 包含内容

**SAGE Kernel** 是 SAGE 框架的核心包，整合了原来的 `sage-core` 和 `sage-cli` 两个包的功能：

### 🏗️ 核心组件 (sage.core)
- **数据流处理框架**: 高性能的 dataflow-native 处理引擎
- **函数管理**: Function registry 和 operator 管理
- **配置系统**: 统一的配置管理和验证

### ⚙️ 任务管理 (sage.jobmanager)  
- **任务调度**: 分布式任务执行和调度
- **执行图**: DAG 执行图构建和优化
- **客户端接口**: JobManager 客户端和服务端

### 🔧 运行时系统 (sage.runtime)
- **服务工厂**: 任务和服务的动态创建
- **通信队列**: 高性能的进程间通信
- **服务管理**: 微服务架构的服务生命周期管理

### 💻 命令行工具 (sage.cli)
- **集群管理**: 分布式集群的部署和管理
- **任务提交**: 命令行任务提交和监控
- **配置管理**: 交互式配置设置和验证
- **扩展管理**: 插件和扩展的安装管理

## 🚀 快速开始

### 安装

```bash
# 从源码安装
pip install -e packages/sage-kernel

# 或者从 PyPI 安装（发布后）
pip install sage-kernel
```

### 使用核心API

```python
from sage.core import Function, Config
from sage.jobmanager import JobManager
from sage.runtime import ServiceTaskFactory

# 创建并使用函数
@Function
def my_processor(data):
    return data * 2

# 使用 JobManager
job_manager = JobManager()
job = job_manager.submit_job(my_processor, data=[1, 2, 3])
```

### 使用命令行工具

```bash
# 启动 SAGE 集群
sage cluster start

# 提交任务
sage job submit my_job.py

# 管理配置
sage config set utils.provider openai
sage config show

# 查看帮助
sage --help
```

## 🏗️ 架构设计

```
sage-kernel/
├── src/sage/
│   ├── core/           # 核心框架
│   ├── jobmanager/     # 任务管理
│   ├── runtime/        # 运行时系统
│   └── cli/            # 命令行工具
├── tests/              # 标准化测试结构
│   ├── core/
│   ├── jobmanager/
│   ├── runtime/
│   └── cli/
└── pyproject.toml      # 统一配置
```

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest tests/core/
pytest tests/cli/

# 运行覆盖率测试
pytest --cov=sage --cov-report=html
```

## 🔧 开发环境

```bash
# 安装开发依赖
pip install -e "packages/sage-kernel[dev]"

# 安装增强CLI功能
pip install -e "packages/sage-kernel[enhanced]"

# 代码格式化
black src/ tests/
ruff check src/ tests/

# 类型检查
mypy src/sage
```

## 📚 依赖关系

### 内部依赖
- `sage-utils`: 基础工具包

### 外部核心依赖
- **ML/AI**: torch, transformers, sentence-transformers, faiss-cpu
- **Web/API**: fastapi, uvicorn, aiohttp, httpx
- **数据处理**: numpy, pandas, scipy, scikit-learn
- **CLI**: typer, rich, click, questionary
- **配置**: pydantic, PyYAML, python-dotenv

## 🎯 设计理念

### 单一内核原则
将核心框架和 CLI 工具合并到一个包中，遵循以下原则：

1. **统一入口**: 所有核心功能通过一个包提供
2. **逻辑分离**: 不同组件保持清晰的模块边界  
3. **依赖优化**: 避免循环依赖，清晰的依赖层次
4. **测试标准化**: 所有测试文件位于标准 `tests/` 目录

### CLI 集成策略
- CLI 功能完全集成到内核包中
- 通过入口点 `sage` 和 `sage-kernel` 提供命令行访问
- CLI 模块不污染核心 API 的导入

## 🔄 从旧包迁移

如果你之前使用 `sage-core` 或 `sage-cli`：

```python
# 旧代码
from sage_core import Function
from sage_cli.main import app

# 新代码  
from sage.core import Function
# CLI 通过命令行使用: sage command
```

## 📋 TODO

- [ ] 完善模块间的导入优化
- [ ] 添加性能基准测试
- [ ] 完善CLI命令的集成测试
- [ ] 优化依赖版本冲突问题
- [ ] 添加更多示例代码

## 🤝 贡献

请查看项目根目录的贡献指南。对于 kernel 相关的开发：

1. 确保测试位于 `tests/` 目录
2. 保持模块间的清晰边界
3. CLI 功能通过入口点而非直接导入使用
4. 遵循现有的代码风格和架构模式

---

🔗 **相关包**: [sage-utils](../sage-utils/) | [sage-extensions](../sage-extensions/) | [sage-lib](../sage-lib/)
