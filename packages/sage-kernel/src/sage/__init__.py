"""
SAGE Kernel - 核心内核包

整合了 SAGE 的核心框架和命令行工具：
- sage.core: 核心数据流处理框架
- sage.jobmanager: 任务管理器
- sage.runtime: 运行时系统
- sage.cli: 命令行界面工具

这是一个命名空间包，支持其他 SAGE 组件的扩展。
"""

__version__ = "1.0.0"

# 命名空间包配置
__path__ = __import__('pkgutil').extend_path(__path__, __name__)

# 导出核心组件
from sage.core import *
from sage.jobmanager import *
from sage.runtime import *

# CLI 工具通过 sage.cli.main:app 入口点使用
# 不在这里直接导入以避免命令行依赖污染
