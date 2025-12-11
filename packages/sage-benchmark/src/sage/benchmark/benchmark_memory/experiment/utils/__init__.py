# utils package

"""实验工具模块

模块分组：
- [A] LLM 调用层 (generators)
  - LLMGenerator: LLM 文本生成，内置 JSON/三元组解析
  - EmbeddingGenerator: Embedding 生成

- [B] 格式化工具 (formatters)
  - format_dialogue(): 对话格式化
  - build_prompt(): Prompt 构建
  - DialogueParser: 向后兼容类（已废弃）

- [C] 配置与参数 (config)
  - RuntimeConfig: 运行时配置
  - get_required_config(): 必需配置校验
  - parse_args(): 命令行参数解析

- [D] 其他辅助
  - path_finder, progress_bar, calculation_table, time_geter
"""

# === [A] LLM 调用层 ===
from .args_parser import parse_args

# === [C] 配置与参数 ===
from .config_loader import RuntimeConfig, get_required_config
from .embedding_generator import EmbeddingGenerator

# === [B] 格式化工具 ===
from .formatters import (
    DialogueParser,  # 向后兼容
    build_prompt,
    format_dialogue,
    format_dialogue_batch,
)

# === 向后兼容：旧模块的导出 ===
# 这些导入保留用于向后兼容，新代码请使用上面的统一接口
from .json_parser import parse_json_response  # 已废弃，请使用 LLMGenerator.generate_json()
from .llm_generator import LLMGenerator
from .triple_parser import TripleParser  # 已废弃，请使用 LLMGenerator.generate_triples()

__all__ = [
    # LLM 调用层
    "LLMGenerator",
    "EmbeddingGenerator",
    # 格式化工具
    "format_dialogue",
    "format_dialogue_batch",
    "build_prompt",
    "DialogueParser",  # 向后兼容
    # 配置与参数
    "RuntimeConfig",
    "get_required_config",
    "parse_args",
    # 向后兼容
    "parse_json_response",
    "TripleParser",
]
