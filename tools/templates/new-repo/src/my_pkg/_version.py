# Single source of truth for this package's version.
#
# Rules (mandatory for all SAGE packages):
#   1. Only this file may contain a hardcoded __version__.
#   2. pyproject.toml must use dynamic version pointing here.
#   3. __init__.py must import from here, never define __version__ itself.
#   4. To bump: update only this file (post-commit hook handles BUILD digit).
#
# Format: X.Y.Z  (public release) or X.Y.Z.N  (build/dev counter)
__version__ = "0.1.0"
