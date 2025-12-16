# utils package

"""实验工具模块

模块分组：
- [A] LLM 调用层 (llm/)
  - LLMGenerator: LLM 文本生成，内置 JSON/三元组解析
  - EmbeddingGenerator: Embedding 生成

- [B] 配置与参数 (config/)
  - RuntimeConfig: 运行时配置管理器
  - get_required_config: 必需配置校验
  - parse_args: 命令行参数解析

- [C] 辅助工具 (helpers/)
  - calculate_test_thresholds: 计算测试阈值
  - get_project_root: 获取项目根目录
  - get_time_filename, get_runtime_timestamp: 时间格式化

- [D] UI 组件 (ui/)
  - ProgressBar: 进度条显示
"""

# === [A] LLM 调用层 ===
# === [B] 配置与参数 ===
from .config import RuntimeConfig, get_required_config, parse_args

# === [C] 辅助工具 ===
from .helpers import (
    calculate_test_thresholds,
    get_project_root,
    get_runtime_timestamp,
    get_time_filename,
)
from .llm import EmbeddingGenerator, LLMGenerator

# === [D] UI 组件 ===
from .ui import ProgressBar

__all__ = [
    # LLM 调用层
    "LLMGenerator",
    "EmbeddingGenerator",
    # 配置与参数
    "RuntimeConfig",
    "get_required_config",
    "parse_args",
    # 辅助工具
    "calculate_test_thresholds",
    "get_project_root",
    "get_runtime_timestamp",
    "get_time_filename",
    # UI 组件
    "ProgressBar",
]
