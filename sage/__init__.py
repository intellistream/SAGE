"""
SAGE - Stream Analysis and Graph Engine
智能流分析和图计算引擎
"""

from sage._version import __version__
__author__ = "IntelliStream"
__email__ = "intellistream@outlook.com"

# 核心模块导入
try:
    from sage.core import *
except ImportError:
    pass

try:
    from sage.jobmanager import *
except ImportError:
    pass

# CLI模块在需要时导入
def get_cli():
    """获取CLI应用"""
    try:
        from sage.cli.main import app
        return app
    except ImportError as e:
        print(f"CLI dependencies not installed: {e}")
        print("Run: python sage/cli/setup.py")
        return None
