"""
SAGE - Streaming-Augmented Generative Execution
"""


# 动态版本加载
def _load_version():
    """从项目根目录动态加载版本信息"""
    from pathlib import Path

    # 获取项目根目录
    current_file = Path(__file__).resolve()
    root_dir = current_file.parent.parent.parent.parent.parent.parent.parent.parent
    version_file = root_dir / "_version.py"

    # 加载版本信息
    if version_file.exists():
        version_globals = {}
        with open(version_file, "r", encoding="utf-8") as f:
            exec(f.read(), version_globals)
        return {
            "version": version_globals.get("__version__", "0.1.3"),
            "author": version_globals.get("__author__", "SAGE Team"),
            "email": version_globals.get("__email__", "shuhao_zhang@hust.edu.cn"),
        }

    # 默认值
    return {
        "version": "0.1.3",
        "author": "SAGE Team",
        "email": "shuhao_zhang@hust.edu.cn",
    }


# 加载信息
_info = _load_version()
__version__ = _info["version"]
__author__ = _info["author"]
__email__ = _info["email"]


def get_apps():
    """动态获取所有命令应用"""
    import importlib
    import pkgutil
    from pathlib import Path
    
    apps = {}
    
    # 获取当前包的路径
    package_path = Path(__file__).parent
    
    # 遍历当前包中的所有模块
    for _, module_name, is_pkg in pkgutil.iter_modules([str(package_path)]):
        if not is_pkg and module_name != '__init__' and module_name != 'common':
            try:
                # 动态导入模块
                module = importlib.import_module(f'.{module_name}', package=__name__)
                
                # 检查模块是否有 app 属性
                if hasattr(module, 'app'):
                    apps[module_name] = module.app
                    
            except ImportError as e:
                # 忽略导入错误，继续处理其他模块
                print(f"Warning: Could not import {module_name}: {e}")
                continue
    
    return apps
