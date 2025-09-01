"""Version information for sage-common package."""

import os
from pathlib import Path

def _get_version():
    """从项目根目录读取版本信息"""
    try:
        # 计算到项目根目录的路径
        current_file = Path(__file__).resolve()
        
        # 从当前文件路径向上查找包含 _version.py 的目录
        search_path = current_file.parent
        for _ in range(10):  # 最多向上查找10层
            version_file = search_path / "_version.py"
            if version_file.exists():
                # 检查是否是项目根目录的版本文件
                try:
                    with open(version_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if '__version__' in content:
                            version_globals = {}
                            exec(content, version_globals)
                            return version_globals.get('__version__', '0.1.3')
                except Exception:
                    pass
            search_path = search_path.parent
            
        # 打包环境的备份版本
        return "0.1.3"
        
    except Exception:
        return "0.1.3"

__version__ = _get_version()
