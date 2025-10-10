"""SAGE Package - Common Module."""

# This is a namespace package that extends the main SAGE package
# Don't define __version__ here as it should come from the main sage package
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

# Only export what's specific to this package
__all__ = ["common"]
