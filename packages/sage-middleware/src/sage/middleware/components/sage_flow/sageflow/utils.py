"""
SAGE Flow 实用工具模块

提供日志配置、版本信息和其他实用功能。
"""

import logging
import sys
from typing import Dict, Any, Optional
import platform


def configure_logging(level: str = "INFO", format_string: Optional[str] = None) -> None:
    """
    配置SAGE Flow的日志系统
    
    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: 自定义日志格式字符串
    """
    if format_string is None:
        format_string = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 设置SAGE Flow特定的logger
    logger = logging.getLogger("sage_flow")
    logger.setLevel(getattr(logging, level.upper()))


def get_version_info() -> Dict[str, Any]:
    """
    获取SAGE Flow版本和环境信息
    
    Returns:
        包含版本和环境信息的字典
    """
    from . import __version__
    
    info = {
        "sage_flow_version": __version__,
        "python_version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.architecture(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }
    
    # 尝试获取C++扩展信息
    try:
        import sage_flow_datastream
        info["cpp_extensions"] = "available"
        # 如果C++模块有版本信息，可以在这里添加
    except ImportError:
        info["cpp_extensions"] = "not_available"
    
    return info


def check_dependencies() -> Dict[str, bool]:
    """
    检查依赖项是否正确安装
    
    Returns:
        依赖项检查结果字典
    """
    dependencies = {}
    
    # 检查必需的Python包
    required_packages = ["numpy", "pybind11"]
    
    for package in required_packages:
        try:
            __import__(package)
            dependencies[package] = True
        except ImportError:
            dependencies[package] = False
    
    # 检查C++扩展
    try:
        import sage_flow_datastream
        dependencies["sage_flow_datastream"] = True
    except ImportError:
        dependencies["sage_flow_datastream"] = False
    
    return dependencies


def print_system_info() -> None:
    """打印系统和依赖信息"""
    print("SAGE Flow System Information")
    print("=" * 40)
    
    # 版本信息
    version_info = get_version_info()
    for key, value in version_info.items():
        print(f"{key}: {value}")
    
    print("\nDependency Check")
    print("-" * 20)
    
    # 依赖检查
    deps = check_dependencies()
    for package, available in deps.items():
        status = "✓" if available else "✗"
        print(f"{status} {package}")


class SageFlowError(Exception):
    """SAGE Flow基础异常类"""
    pass


class ConfigurationError(SageFlowError):
    """配置错误异常"""
    pass


class ExtensionError(SageFlowError):
    """C++扩展错误异常"""
    pass


class DataProcessingError(SageFlowError):
    """数据处理错误异常"""
    pass


def require_extensions() -> None:
    """
    检查C++扩展是否可用，如果不可用则抛出异常
    
    Raises:
        ExtensionError: 当C++扩展不可用时
    """
    try:
        import sage_flow_datastream
    except ImportError as e:
        raise ExtensionError(
            "SAGE Flow C++ extensions are not available. "
            "Please ensure the package is properly compiled. "
            f"Original error: {e}"
        ) from e


# 创建默认logger
logger = logging.getLogger("sage_flow")