"""
{package_description}
"""

# 动态加载版本信息 - 避免硬编码
import sys
from pathlib import Path

def _load_version_info():
    """动态加载版本信息"""
    # 查找_version.py文件
    current_path = Path(__file__).resolve()
    
    # 向上查找项目根目录
    for parent in current_path.parents:
        version_file = parent / "_version.py"
        if version_file.exists():
            version_globals = {{}}
            with open(version_file, 'r', encoding='utf-8') as f:
                exec(f.read(), version_globals)
            return version_globals
    
    # 如果找不到，返回默认值
    return {{
        '__version__': 'unknown',
        '__project_name__': 'SAGE',
        '__project_full_name__': 'Streaming-Augmented Generative Execution',
        '__author__': 'SAGE Team',
        '__email__': 'shuhao_zhang@hust.edu.cn'
    }}

# 加载版本信息
_version_info = _load_version_info()

# 导出版本信息
__version__ = _version_info.get('__version__', 'unknown')
__author__ = _version_info.get('__author__', 'SAGE Team')
__email__ = _version_info.get('__email__', 'shuhao_zhang@hust.edu.cn')

# 提供便捷函数
def get_project_name():
    """获取项目名称"""
    return _version_info.get('__project_name__', 'SAGE')

def get_project_full_name():
    """获取项目完整名称"""
    return _version_info.get('__project_full_name__', 'Streaming-Augmented Generative Execution')

def get_project_description():
    """获取项目描述"""
    return f"{{get_project_name()}} - {{get_project_full_name()}}"

# 包描述（可以在子类中重写）
__doc__ = get_project_description()
