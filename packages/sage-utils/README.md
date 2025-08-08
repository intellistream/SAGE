# SAGE Utils

通用工具库，为SAGE框架提供基础的配置管理、日志记录等功能。

## 功能特性

### 🔧 配置管理 (Config)
- **多格式支持**: 支持YAML、JSON、TOML等配置文件格式
- **智能路径查找**: 支持项目级、用户级、系统级配置文件自动发现
- **环境变量覆盖**: 支持通过环境变量动态覆盖配置项
- **配置验证**: 基于Pydantic的配置项验证和类型检查
- **缓存机制**: 高效的配置加载和缓存策略

### 📝 日志记录 (Logging)
- **多输出目标**: 支持控制台、文件等多种输出目标
- **彩色输出**: 支持不同日志级别的颜色区分
- **IDE友好**: 格式化输出支持IDE点击跳转
- **线程安全**: 全局调试开关的线程安全控制
- **动态配置**: 运行时动态调整日志输出配置

## 安装

```bash
pip install intellistream-sage-utils
```

## 快速开始

### 配置管理

```python
from sage.utils.config.loader import load_config
from sage.utils.config.manager import ConfigManager, BaseConfig

# 简单配置加载
config = load_config("config.yaml")  # 自动查找配置文件

# 使用配置管理器
manager = ConfigManager("./config")
config = manager.load("app.yaml")
manager.save("app.yaml", {"key": "value"})

# 使用配置类
class AppConfig(BaseConfig):
    app_name: str = "myapp"
    debug: bool = False
    port: int = 8000

config = AppConfig(app_name="sage", debug=True)
```

### 日志记录

```python
from sage.utils.logging.custom_logger import CustomLogger

# 基本用法
logger = CustomLogger([
    ("console", "INFO"),           # 控制台输出
    ("app.log", "DEBUG"),         # 文件输出(相对路径)
    ("/tmp/error.log", "ERROR")   # 文件输出(绝对路径)
], name="MyApp", log_base_folder="./logs")

logger.info("应用启动")
logger.error("发生错误", exc_info=True)

# 全局调试控制
CustomLogger.disable_global_console_debug()  # 关闭所有控制台调试输出
CustomLogger.enable_global_console_debug()   # 启用所有控制台调试输出
```

## 模块结构

```
sage/
└── utils/
    ├── config/
    │   ├── __init__.py
    │   ├── loader.py      # 配置文件加载器
    │   └── manager.py     # 配置管理器
    └── logging/
        ├── custom_formatter.py  # 自定义日志格式化器
        └── custom_logger.py     # 自定义日志记录器
```

## 配置文件查找优先级

配置加载器按以下优先级查找配置文件：

1. **显式路径**: 直接指定的配置文件路径
2. **环境变量**: `SAGE_CONFIG` 环境变量指定的路径
3. **项目级配置**: `<项目根目录>/config/config.yaml`
4. **用户级配置**: `~/.config/sage/config.yaml`
5. **系统级配置**: `/etc/sage/config.yaml` (Linux/macOS)

## 日志输出格式

日志输出采用IDE友好的两行格式：

```
2024-08-08 10:30:45 | INFO  | MyApp | /path/to/file.py:123 →
    应用启动成功，监听端口：8000
```

## 开发

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest
pytest --cov=sage.utils  # 带覆盖率
```

### 代码格式化

```bash
black src/ tests/
isort src/ tests/
flake8 src/ tests/
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件。
