"""
SAGE - Intelligent Stream Analytics Gateway Engine

这是 SAGE 的主要入口模块，提供统一的 API 接口。
"""

# This is a namespace package
__path__ = __import__('pkgutil').extend_path(__path__, __name__)

__version__ = "0.1.0"
__author__ = "SAGE Team"
__email__ = "sage@intellistream.com"

import os
import warnings

# 检查并提示可选功能包
def _check_optional_packages():
    """检查可选功能包的安装状态并提供提示"""
    missing_features = []
    
    try:
        import sage.cli
    except ImportError:
        missing_features.append("CLI 工具 (pip install intsage-common[basic])")
    
    try:
        import sage.dev
    except ImportError:
        missing_features.append("开发工具 (pip install intsage-common[dev])")
    
    try:
        import sage.frontend
    except ImportError:
        missing_features.append("Web 前端 (pip install intsage-common[frontend])")
    
    # 只在交互模式下显示提示，避免在脚本中干扰输出
    if missing_features and hasattr(sys, 'ps1') and not os.environ.get('SAGE_QUIET'):
        print("\n💡 SAGE 可选功能包:")
        for feature in missing_features:
            print(f"  • {feature}")
        print("  • 完整安装: pip install intsage-common[full]")
        print("  • 禁用提示: export SAGE_QUIET=1\n")

def _check_optional_packages():
    """检查可选功能包的安装状态并提供提示"""
    import sys
    missing_features = []
    
    # 检查 CLI 工具
    try:
        import sage.cli  # type: ignore
    except ImportError:
        missing_features.append("CLI 工具 (pip install intsage-common[basic])")
    
    # 检查开发工具
    try:
        import sage.dev  # type: ignore
    except ImportError:
        missing_features.append("开发工具 (pip install intsage-common[dev])")
    
    # 检查 Web 前端
    try:
        import sage.frontend  # type: ignore
    except ImportError:
        missing_features.append("Web 前端 (pip install intsage-common[frontend])")
    
    # 只在交互模式下显示提示，避免在脚本中干扰输出
    if missing_features and hasattr(sys, 'ps1') and not os.environ.get('SAGE_QUIET'):
        print("\n💡 SAGE 可选功能包:")
        for feature in missing_features:
            print(f"  • {feature}")
        print("  • 完整安装: pip install intsage-common[full]")
        print("  • 禁用提示: export SAGE_QUIET=1\n")

# 导入核心功能
try:
    # 直接从kernel包导入，而不通过sage.kernel
    from sage.kernel import create_app, TaskContext
    from sage.middleware import get_service_factory
    
    # 尝试导入 utils，如果没有安装 sage-common 则提供基础实现
    try:
        from sage.common.utils.logging import get_logger
        def now():
            import datetime
            return datetime.datetime.now()
    except ImportError:
        def now():
            import datetime
            return datetime.datetime.now()
        
        def get_logger(name):
            import logging
            return logging.getLogger(name)
    
    # 首次导入时检查可选包
    _check_optional_packages()
    
except ImportError as e:
    # 不显示警告，因为这会干扰Ray Actor
    pass
    
    # 提供基础功能
    def create_app():
        raise ImportError("isage-kernel package is required. Please install with: pip install isage-kernel")
    
    def get_service_factory():
        raise ImportError("isage-middleware package is required. Please install with: pip install isage-middleware")
    
    def now():
        import datetime
        return datetime.datetime.now()
    
    def get_logger(name):
        import logging
        return logging.getLogger(name)

# 导出主要接口
__all__ = [
    "__version__",
    "create_app", 
    "TaskContext",
    "get_service_factory",
    "now",
    "get_logger",
]
