"""
SAGE Middleware Components - 运行时兼容性检测
"""

import warnings
from typing import Any, Optional

# 尝试导入C++扩展，失败时使用纯Python实现
_SAGE_DB_AVAILABLE = False
_SAGE_FLOW_AVAILABLE = False

try:
    from sage.middleware.components.sage_db.python import _sage_db

    _SAGE_DB_AVAILABLE = True
except ImportError:
    _sage_db = None
    warnings.warn(
        "SAGE DB C++扩展不可用，某些高性能功能将受限。"
        "安装完整版本：pip install --force-reinstall isage-middleware",
        UserWarning,
    )

try:
    from sage.middleware.components.sage_flow.python import _sage_flow
    from sage.middleware.components.sage_flow.python.sage_flow import *

    _SAGE_FLOW_AVAILABLE = True
except ImportError:
    _sage_flow = None
    warnings.warn(
        "SAGE Flow C++扩展不可用，流处理功能将受限。"
        "安装完整版本：pip install --force-reinstall isage-middleware",
        UserWarning,
    )


def is_sage_db_available() -> bool:
    """检查SAGE DB扩展是否可用"""
    return _SAGE_DB_AVAILABLE


def is_sage_flow_available() -> bool:
    """检查SAGE Flow扩展是否可用"""
    return _SAGE_FLOW_AVAILABLE


def get_extension_status() -> dict:
    """获取所有扩展的状态"""
    return {
        "sage_db": _SAGE_DB_AVAILABLE,
        "sage_flow": _SAGE_FLOW_AVAILABLE,
        "total_available": sum([_SAGE_DB_AVAILABLE, _SAGE_FLOW_AVAILABLE]),
        "total_extensions": 2,
    }


def check_extensions_availability() -> dict:
    """检查扩展可用性，返回兼容格式用于CI"""
    return {
        "sage_db": _SAGE_DB_AVAILABLE,
        "sage_flow": _SAGE_FLOW_AVAILABLE,
    }


def require_sage_db():
    """要求SAGE DB扩展可用，否则抛出异常"""
    if not _SAGE_DB_AVAILABLE:
        raise ImportError(
            "此功能需要SAGE DB C++扩展。请安装完整版本：\n"
            "pip install --force-reinstall isage-middleware\n"
            "或安装构建依赖后重新安装：\n"
            "Ubuntu/Debian: sudo apt-get install build-essential cmake\n"
            "macOS: brew install cmake"
        )
    return _sage_db


def require_sage_flow():
    """要求SAGE Flow扩展可用，否则抛出异常"""
    if not _SAGE_FLOW_AVAILABLE:
        raise ImportError(
            "此功能需要SAGE Flow C++扩展。请安装完整版本：\n"
            "pip install --force-reinstall isage-middleware\n"
            "或安装构建依赖后重新安装：\n"
            "Ubuntu/Debian: sudo apt-get install build-essential cmake\n"
            "macOS: brew install cmake"
        )
    return _sage_flow


# 在模块导入时显示状态
if __name__ != "__main__":
    status = get_extension_status()
    if status["total_available"] < status["total_extensions"]:
        print(
            f"ℹ️  SAGE扩展状态: {status['total_available']}/{status['total_extensions']} 可用"
        )
        if not _SAGE_DB_AVAILABLE:
            print("  ❌ SAGE DB: C++扩展不可用")
        if not _SAGE_FLOW_AVAILABLE:
            print("  ❌ SAGE Flow: C++扩展不可用")
        print("  💡 提示: 安装构建依赖后重新安装可启用完整功能")
