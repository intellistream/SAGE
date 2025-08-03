# SAGE Utils - 通用工具库

SAGE框架的通用工具库，提供各种常用的辅助功能和工具类。

## 🎯 功能特性

### 核心工具模块

- **配置管理** (`sage.utils.config`) - 统一的配置加载和管理
- **日志系统** (`sage.utils.logging`) - 结构化日志和输出格式化  
- **文件处理** (`sage.utils.files`) - 文件操作和路径管理
- **数据处理** (`sage.utils.data`) - 数据转换和验证工具
- **类型工具** (`sage.utils.types`) - 类型定义和验证
- **异步工具** (`sage.utils.async_utils`) - 异步编程辅助
- **缓存系统** (`sage.utils.cache`) - 内存和磁盘缓存
- **测试工具** (`sage.utils.testing`) - 测试辅助和Fixtures

## 🚀 快速开始

### 安装

```bash
# 在SAGE monorepo根目录
python scripts/package-manager.py install sage-utils

# 或直接pip安装开发版本
pip install -e packages/sage-utils
```

### 基本使用

```python
# 通过命名空间包访问 (保持向后兼容)
from sage.utils.config import load_config
from sage.utils.logging import get_logger
from sage.utils.files import ensure_dir

# 配置管理
config = load_config("config.yaml")

# 日志系统
logger = get_logger(__name__)
logger.info("SAGE Utils 工作正常")

# 文件操作
data_dir = ensure_dir("./data")
```

## 📁 包结构

```
packages/sage-utils/
├── src/sage/utils/              # 命名空间包源码
│   ├── __init__.py             # 包初始化
│   ├── config/                 # 配置管理模块
│   ├── logging/                # 日志系统模块
│   ├── files/                  # 文件处理模块
│   ├── data/                   # 数据处理模块
│   ├── types/                  # 类型工具模块
│   ├── async_utils/            # 异步工具模块
│   ├── cache/                  # 缓存系统模块
│   └── testing/                # 测试工具模块
├── tests/                      # 测试代码
├── docs/                       # 文档
├── pyproject.toml              # 项目配置
└── README.md                   # 本文件
```

## 🛠️ 开发

### 设置开发环境

```bash
# 安装开发依赖
python scripts/package-manager.py setup-dev sage-utils

# 或使用pip
pip install -e "packages/sage-utils[dev]"
```

### 运行测试

```bash
# 使用包管理器
python scripts/package-manager.py test sage-utils

# 或直接使用pytest
cd packages/sage-utils
pytest tests/ -v
```

### 代码质量检查

```bash
# 格式化代码
black src/ tests/
isort src/ tests/

# 类型检查
mypy src/

# Linting
ruff src/ tests/
```

## 🔧 与其他SAGE包的集成

`sage-utils`被设计为SAGE生态系统的基础工具包：

```python
# 在 sage-core 中使用
from sage.utils.config import load_config
from sage.utils.logging import get_logger

# 在 sage-extensions 中使用  
from sage.utils.types import ensure_type
from sage.utils.cache import LRUCache

# 在 sage-dashboard 中使用
from sage.utils.async_utils import run_async
from sage.utils.data import validate_json
```

## 📚 API文档

详细的API文档请参考：[SAGE Utils API文档](https://sage-docs.intellistream.cc/utils)

## 🧪 测试覆盖率

我们致力于保持高质量的测试覆盖率：

```bash
# 运行覆盖率测试
pytest --cov=sage.utils --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

## 🔄 版本兼容性

- **Python**: 3.11+
- **依赖**: 最小化依赖，只包含必要的工具库
- **向后兼容**: 保持`sage.utils`命名空间的完全兼容

## 🤝 贡献指南

1. Fork并克隆仓库
2. 创建feature分支: `git checkout -b feature/new-util`
3. 开发新功能并添加测试
4. 确保所有测试通过: `python scripts/package-manager.py test sage-utils`
5. 提交PR到主仓库

## 📄 许可证

MIT License - 详见根目录的 [LICENSE](../../LICENSE) 文件。

## 🔗 相关包

- [sage-core](../sage-core/) - SAGE核心框架
- [sage-extensions](../sage-extensions/) - 高性能C++扩展
- [sage-dashboard](../sage-dashboard/) - Web界面和API

---

**注意**: 这是SAGE智能化Monorepo的一部分，所有工具都通过统一的`scripts/package-manager.py`进行管理。
