"""
SAGE - Stream Analysis and Graph Engine
智能流分析和图计算引擎
"""

__version__ = "0.1.1"
__author__ = "IntelliStream"
__email__ = "intellistream@outlook.com"

try:
    from sage.kernel.kernels.jobmanager import *
except ImportError:
    pass

# CLI模块在需要时导入
def get_cli():
    """获取CLI应用"""
    try:
        from sage.kernel.cli.main import app
        return app
    except ImportError as e:
        print(f"CLI dependencies not installed: {e}")
        print("Run: python sage/cli/setup.py")
        return None
