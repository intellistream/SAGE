"""
SAGE Frontend Server Module

FastAPI-based backend server for SAGE Frontend.
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径，以便导入现有的sage_server模块
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入现有的main模块
try:
    from sage_server.main import main, create_app
    
    __all__ = ["main", "create_app"]
    
except ImportError as e:
    print(f"Warning: Could not import sage_server.main: {e}")
    print("Make sure the sage_server directory is in the correct location.")
    
    def main():
        """Fallback main function"""
        print("SAGE Frontend Server")
        print("Error: Could not import the main server module.")
        print("Please check the installation and try again.")
        return 1
    
    __all__ = ["main"]
