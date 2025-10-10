"""SAGE Package - Common Module."""

# This is a namespace package that extends the main SAGE package
# Don't define __version__ here as it should come from the main sage package

# 使用 pkg_resources 方式声明命名空间包（更可靠）
try:
    __import__('pkg_resources').declare_namespace(__name__)
except ImportError:
    # 如果 pkg_resources 不可用，回退到 pkgutil 方式
    __path__ = __import__("pkgutil").extend_path(__path__, __name__)

# Only export what's specific to this package
__all__ = ["common"]
