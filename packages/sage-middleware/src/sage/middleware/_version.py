"""Version information for sage-middleware package."""

import os
from pathlib import Path

def _get_version():
    """智能版本获取 - 开发环境从根目录读取，构建环境使用内嵌版本"""
    try:
        # 尝试从项目根目录读取版本（开发环境）
        current_file = Path(__file__).resolve()
        
        # 从当前文件的上级目录开始查找（跳过自己所在的目录）
        search_path = current_file.parent.parent  # 直接从上级目录开始
        for _ in range(10):  # 最多向上查找10层
            root_version_file = search_path / "_version.py"
            if root_version_file.exists():
                # 确保不是自己，并且检查是否是项目根目录的版本文件
                if root_version_file != current_file:
                    try:
                        with open(root_version_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 检查是否是根目录版本文件（以注释开头，包含项目信息）
                            if content.startswith('"""') and 'SAGE Version Information' in content and '__version__' in content:
                                version_globals = {}
                                exec(content, version_globals)
                                return version_globals.get('__version__', '0.1.3')
                    except Exception:
                        pass
            search_path = search_path.parent
            
        # 如果找不到根目录版本文件，使用内嵌的备份版本（构建环境）
        return "0.1.3"
        
    except Exception:
        # 最终备份版本
        return "0.1.3"

__version__ = _get_version()
