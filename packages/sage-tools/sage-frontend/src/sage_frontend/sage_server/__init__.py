"""
SAGE Frontend Server Module

FastAPI-based backend server for SAGE Frontend.
"""

import os
import sys
from pathlib import Path

def _lazy_import_sage_server():
    """延迟导入sage_server模块，避免在包初始化时出错"""
    # 添加项目根目录到Python路径，以便导入现有的sage_server模块
    project_root = Path(__file__).parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    try:
        from sage_server.main import main as sage_server_main
        return sage_server_main
    except ImportError:
        # 如果导入失败，返回None，让调用者处理
        return None

# 不要在模块级别导入，而是提供一个函数来获取
def get_sage_server_main():
    """获取sage_server的main函数"""
    return _lazy_import_sage_server()

__all__ = ["get_sage_server_main"]
