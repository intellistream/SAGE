"""
SAGE namespace package

This is a namespace package that allows multiple SAGE sub-packages
to be installed independently while sharing the same 'sage' namespace.
"""

# This file can be empty or contain the namespace declaration
# For PEP 420 namespace packages, this file technically isn't needed,
# but including it helps with IDE support and explicit namespace declaration.

__path__ = __import__("pkgutil").extend_path(__path__, __name__)
