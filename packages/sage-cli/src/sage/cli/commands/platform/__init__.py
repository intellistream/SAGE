"""
SAGE Platform Commands

平台管理命令组，包括：
- cluster: 集群管理
- head: 头节点管理
- worker: Worker节点管理
- job: 作业管理
- jobmanager: JobManager服务
- config: 配置管理
- doctor: 系统诊断
- version: 版本信息
- extensions: C++扩展管理
"""

from rich.console import Console

# 创建主命令应用 - 注意：这个不会被直接注册，而是每个子命令会被单独注册
# 但我们保留这个结构以便将来可能的重组

console = Console()

# 导入所有平台命令
try:
    from .cluster import app as cluster_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 cluster 命令: {e}[/yellow]")
    cluster_app = None

try:
    from .head import app as head_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 head 命令: {e}[/yellow]")
    head_app = None

try:
    from .worker import app as worker_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 worker 命令: {e}[/yellow]")
    worker_app = None

try:
    from .job import app as job_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 job 命令: {e}[/yellow]")
    job_app = None

try:
    from .jobmanager import app as jobmanager_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 jobmanager 命令: {e}[/yellow]")
    jobmanager_app = None

try:
    from .config import app as config_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 config 命令: {e}[/yellow]")
    config_app = None

try:
    from .doctor import app as doctor_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 doctor 命令: {e}[/yellow]")
    doctor_app = None

try:
    from .version import app as version_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 version 命令: {e}[/yellow]")
    version_app = None

try:
    from .extensions import app as extensions_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 extensions 命令: {e}[/yellow]")
    extensions_app = None

try:
    from .docs import app as docs_app
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 docs 命令: {e}[/yellow]")
    docs_app = None

# 导出所有命令
__all__ = [
    "cluster_app",
    "head_app",
    "worker_app",
    "job_app",
    "jobmanager_app",
    "config_app",
    "doctor_app",
    "version_app",
    "extensions_app",
    "docs_app",
]
