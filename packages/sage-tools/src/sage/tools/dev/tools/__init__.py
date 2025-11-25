"""
SAGE - Streaming-Augmented Generative Execution
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.tools._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# 导出质量检查工具
from .architecture_checker import ArchitectureChecker
from .devnotes_checker import DevNotesChecker

# 导出开发工具类
from .enhanced_package_manager import EnhancedPackageManager
from .enhanced_test_runner import EnhancedTestRunner
from .package_dependency_validator import PackageDependencyValidator
from .package_readme_checker import PackageREADMEChecker
from .vscode_path_manager import VSCodePathManager

__all__ = [
    "EnhancedPackageManager",
    "EnhancedTestRunner",
    "VSCodePathManager",
    "ArchitectureChecker",
    "DevNotesChecker",
    "PackageREADMEChecker",
    "PackageDependencyValidator",
]
