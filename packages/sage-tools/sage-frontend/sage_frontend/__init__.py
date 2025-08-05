"""
SAGE Frontend Package

Web前端和仪表板界面组件，提供可视化的数据处理管道管理和监控功能。

主要组件:
- Dashboard: Angular前端界面
- API Server: FastAPI后端服务
- Operators: 操作符Web界面管理
- Visualization: 数据可视化功能
"""

__version__ = "1.0.0"
__author__ = "IntelliStream Team"
__email__ = "intellistream@outlook.com"

# 包的主要模块导入
try:
    # 尝试导入主要组件
    from . import sage_server
    from . import dashboard
    from . import operators
except ImportError:
    # 如果导入失败，说明可能是开发环境或包结构需要调整
    pass

__all__ = [
    "__version__",
    "__author__", 
    "__email__",
    "sage_server",
    "dashboard", 
    "operators",
]
