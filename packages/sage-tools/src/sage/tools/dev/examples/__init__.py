"""
SAGE Examples Testing Tools

这个模块提供了用于测试 examples/ 目录的工具集。

⚠️  注意：这些工具仅在 SAGE 开发环境中可用。

使用要求：
-----------
1. 从源码安装 SAGE：
   git clone https://github.com/intellistream/SAGE
   cd SAGE
   pip install -e packages/sage-tools[dev]

2. 或设置 SAGE_ROOT 环境变量指向 SAGE 项目根目录

使用方式：
-----------
命令行：
    sage-dev examples analyze              # 分析示例结构
    sage-dev examples test --quick         # 运行快速测试
    sage-dev examples test --category rag  # 测试特定类别
    sage-dev examples check                # 检查中间结果放置

Python API：
    from sage.tools.dev.examples import ExampleTestSuite

    suite = ExampleTestSuite()
    stats = suite.run_all_tests(quick_only=True)
"""

from .analyzer import ExampleAnalyzer
from .models import ExampleInfo, ExampleTestResult
from .runner import ExampleRunner
from .strategies import ExampleTestStrategies, TestStrategy
from .suite import ExampleTestSuite
from .utils import (
    ensure_development_environment,
    find_examples_directory,
    find_project_root,
    get_development_info,
)

__all__ = [
    # Core classes
    "ExampleAnalyzer",
    "ExampleRunner",
    "ExampleTestSuite",
    "ExampleTestStrategies",
    # Data classes
    "ExampleInfo",
    "ExampleTestResult",
    "TestStrategy",
    # Utilities
    "find_examples_directory",
    "find_project_root",
    "ensure_development_environment",
    "get_development_info",
]

# Version info
__version__ = "0.1.0"

# Development environment check on import
try:
    ensure_development_environment()
except RuntimeError:
    # Don't fail on import, but warn
    import warnings

    warnings.warn(
        "SAGE Examples testing tools require a development environment. "
        "Please clone the SAGE repository or set SAGE_ROOT environment variable.",
        RuntimeWarning,
        stacklevel=2,
    )
