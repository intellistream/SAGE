"""
SAGE Application Commands

应用层命令组，包括：
- llm: LLM服务管理
- chat: 编程助手
- embedding: Embedding管理
- pipeline: Pipeline构建器
- studio: 可视化编辑器
- inference: 统一推理服务管理
"""

from rich.console import Console

console = Console()

# 导入所有应用命令
try:
    from .llm import app as llm_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 llm 命令: {e}[/yellow]")
    llm_app = None

try:
    from .chat import app as chat_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 chat 命令: {e}[/yellow]")
    chat_app = None

try:
    from .embedding import app as embedding_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 embedding 命令: {e}[/yellow]")
    embedding_app = None

try:
    from .pipeline import app as pipeline_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 pipeline 命令: {e}[/yellow]")
    pipeline_app = None

try:
    from .studio import app as studio_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 studio 命令: {e}[/yellow]")
    studio_app = None

try:
    from .inference import app as inference_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 inference 命令: {e}[/yellow]")
    inference_app = None

try:
    from .gateway import app as gateway_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 gateway 命令: {e}[/yellow]")
    gateway_app = None

try:
    from .edge import app as edge_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 edge 命令: {e}[/yellow]")
    edge_app = None

# 导出所有命令
__all__ = [
    "llm_app",
    "chat_app",
    "embedding_app",
    "pipeline_app",
    "studio_app",
    "inference_app",
    "gateway_app",
    "edge_app",
]
