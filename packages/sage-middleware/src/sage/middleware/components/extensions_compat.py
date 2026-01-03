"""
SAGE Middleware Components - 运行时兼容性检测

此模块处理C++扩展的可选导入，提供优雅的降级机制。
C++扩展模块（_sage_flow）在未编译时可能不存在，
此模块确保在扩展不可用时也能正常导入和运行。

注意：
- SageDB 已独立为 PyPI 包 (isagedb)，不再作为 SAGE C++ 扩展。
- SageTSDB 已独立为 PyPI 包 (isage-tsdb)，不再作为 SAGE C++ 扩展。
"""

import warnings
from typing import TYPE_CHECKING, Any

# 类型检查时导入，运行时通过try/except处理
if TYPE_CHECKING:
    # 当扩展编译可用时，这些导入会成功
    # stub文件（.pyi）提供类型提示
    from sage.middleware.components.sage_flow.python import sage_flow as _sage_flow
else:
    # 运行时动态导入，优雅处理缺失的扩展
    _sage_flow: Any = None

# 尝试导入C++扩展，失败时使用纯Python实现
_SAGE_DB_AVAILABLE = False  # 通过 isagedb 包检测
_SAGE_FLOW_AVAILABLE = False
_SAGE_TSDB_AVAILABLE = False  # 通过 isage-tsdb 包检测

if not TYPE_CHECKING:
    # SageDB 现在是独立的 PyPI 包
    try:
        import sagedb  # noqa: F401

        _SAGE_DB_AVAILABLE = True
    except ImportError:
        warnings.warn(
            "SageDB 不可用。请安装: pip install isagedb",
            UserWarning,
            stacklevel=2,
        )

    try:
        # 只导入 Python wrapper 模块，避免重复加载 C++ 扩展
        from sage.middleware.components.sage_flow.python import sage_flow as _sage_flow

        _SAGE_FLOW_AVAILABLE = True
    except ImportError as e:
        _sage_flow = None
        warnings.warn(
            f"SAGE Flow C++扩展不可用，流处理功能将受限。错误: {e}\n"
            "安装完整版本：pip install --force-reinstall isage-middleware",
            UserWarning,
            stacklevel=2,
        )

    # SageTSDB 现在是独立的 PyPI 包
    try:
        import sage_tsdb  # noqa: F401

        _SAGE_TSDB_AVAILABLE = True
    except ImportError:
        warnings.warn(
            "SAGE TSDB 不可用。请安装: pip install isage-tsdb",
            UserWarning,
            stacklevel=2,
        )


def is_sage_db_available() -> bool:
    """检查SAGE DB扩展是否可用"""
    return _SAGE_DB_AVAILABLE


def is_sage_flow_available() -> bool:
    """检查SAGE Flow扩展是否可用"""
    return _SAGE_FLOW_AVAILABLE


def is_sage_tsdb_available() -> bool:
    """检查SAGE TSDB扩展是否可用"""
    return _SAGE_TSDB_AVAILABLE


def get_extension_status() -> dict:
    """获取所有扩展的状态"""
    return {
        "sage_db": _SAGE_DB_AVAILABLE,
        "sage_flow": _SAGE_FLOW_AVAILABLE,
        "sage_tsdb": _SAGE_TSDB_AVAILABLE,
        "total_available": sum([_SAGE_DB_AVAILABLE, _SAGE_FLOW_AVAILABLE, _SAGE_TSDB_AVAILABLE]),
        "total_extensions": 3,
    }


def check_extensions_availability() -> dict:
    """检查扩展可用性，返回兼容格式用于CI"""
    return {
        "sage_db": _SAGE_DB_AVAILABLE,
        "sage_flow": _SAGE_FLOW_AVAILABLE,
        "sage_tsdb": _SAGE_TSDB_AVAILABLE,
    }


def require_sage_db():
    """要求SageDB可用，否则抛出异常"""
    if not _SAGE_DB_AVAILABLE:
        raise ImportError("此功能需要 SageDB。请安装: pip install isagedb")
    import sagedb

    return sagedb


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


def require_sage_tsdb():
    """要求SAGE TSDB可用，否则抛出异常"""
    if not _SAGE_TSDB_AVAILABLE:
        raise ImportError("此功能需要 SAGE TSDB。请安装: pip install isage-tsdb")
    import sage_tsdb

    return sage_tsdb


# 在模块导入时显示状态
if __name__ != "__main__":
    status = get_extension_status()
    if status["total_available"] < status["total_extensions"]:
        print(f"ℹ️  SAGE扩展状态: {status['total_available']}/{status['total_extensions']} 可用")
        if not _SAGE_DB_AVAILABLE:
            print("  ❌ SageDB: 未安装 (pip install isagedb)")
        if not _SAGE_FLOW_AVAILABLE:
            print("  ❌ SAGE Flow: C++扩展不可用")
        if not _SAGE_TSDB_AVAILABLE:
            print("  ❌ SAGE TSDB: 未安装 (pip install isage-tsdb)")
        print("  💡 提示: 安装相应依赖可启用完整功能")
