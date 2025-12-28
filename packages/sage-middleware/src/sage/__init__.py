"""SAGE namespace package."""

# This is a namespace package
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

# Import version from the sage meta-package if available
# This allows `sage.__version__` to work even though this is a namespace package
try:
    from sage._version import __author__, __email__, __version__
except ImportError:
    # If sage meta-package is not installed, these won't be available
    pass
