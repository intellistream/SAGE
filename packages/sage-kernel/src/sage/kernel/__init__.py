"""
SAGE - Streaming-Augmented Generative Execution
"""

# 动态版本加载
def _load_version():
    """从 sage-common 包加载版本信息"""
    try:
        # 优先从 sage-common 包加载版本
        from sage.kernel._version import __version__
        return {
            'version': __version__,
            'author': 'SAGE Team',
            'email': 'shuhao_zhang@hust.edu.cn'
        }
    except ImportError:
        # 如果 sage-common 不可用，从项目根目录加载（开发环境）
        try:
            from pathlib import Path
            current_file = Path(__file__).resolve()
            # 根据当前文件位置计算到项目根目录的层数
            parts = current_file.parts
            sage_index = -1
            for i, part in enumerate(parts):
                if part == 'SAGE':
                    sage_index = i
                    break
            
            if sage_index >= 0:
                root_dir = Path(*parts[:sage_index+1])
                version_file = root_dir / "_version.py"
                
                if version_file.exists():
                    version_globals = {}
                    with open(version_file, 'r', encoding='utf-8') as f:
                        exec(f.read(), version_globals)
                    return {
                        'version': version_globals.get('__version__', '0.1.3'),
                        'author': version_globals.get('__author__', 'SAGE Team'),
                        'email': version_globals.get('__email__', 'shuhao_zhang@hust.edu.cn')
                    }
        except Exception:
            pass
    
    # 最后的默认值
    return {
        'version': '0.1.3',
        'author': 'SAGE Team', 
        'email': 'shuhao_zhang@hust.edu.cn'
    }

# 加载信息
_info = _load_version()
__version__ = _info['version']
__author__ = _info['author']
__email__ = _info['email']

# 导出核心组件
try:
    from .jobmanager.jobmanager_client import JobManagerClient
except ImportError:
    # 如果导入失败，使用兼容性层
    try:
        from sage.core.api.compatibility import safe_import_jobmanager_client
        JobManagerClient = safe_import_jobmanager_client()
    except ImportError:
        # 最后的备用方案
        class JobManagerClient:
            def __init__(self, *args, **kwargs):
                raise ImportError("JobManagerClient is not available. Please check your installation.")

__all__ = ['__version__', '__author__', '__email__', 'JobManagerClient']
