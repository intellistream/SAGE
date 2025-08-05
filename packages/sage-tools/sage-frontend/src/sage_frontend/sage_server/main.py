"""
SAGE Frontend Server Main Entry Point

This module provides the main entry point for the SAGE Frontend server.
"""

import os
import sys
from pathlib import Path

def main():
    """Main entry point for sage-frontend server"""
    
    # 获取当前文件的路径，用于定位项目结构
    current_file = Path(__file__)
    frontend_root = current_file.parent.parent.parent.parent
    sage_server_path = frontend_root / "sage_server"
    
    # 添加sage_server路径到Python路径
    if str(sage_server_path) not in sys.path:
        sys.path.insert(0, str(sage_server_path))
    
    # 切换到sage_server目录（因为有些相对路径依赖）
    original_cwd = os.getcwd()
    try:
        os.chdir(sage_server_path)
        
        # 导入并运行原始的main函数
        from main import main as original_main
        return original_main()
        
    except ImportError as e:
        print(f"Error: Could not import sage_server main module: {e}")
        print(f"Expected location: {sage_server_path}")
        print("Please check the installation and file structure.")
        return 1
    except Exception as e:
        print(f"Error running server: {e}")
        return 1
    finally:
        # 恢复原始工作目录
        os.chdir(original_cwd)

if __name__ == "__main__":
    exit(main())
