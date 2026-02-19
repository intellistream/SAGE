"""SAGE - Streaming-Augmented Generative Execution.

Meta-package that re-exports the version string and keeps the ``sage``
namespace open for all sub-packages (sage-common, sage-platform, etc.).
"""

from __future__ import annotations

# Preserve namespace-package semantics so sub-packages installed in other
# directories (sage-common, sage-platform, …) are still discoverable even
# though this file now turns `sage` into a regular package from the
# meta-package's perspective.
import pkgutil

__path__ = pkgutil.extend_path(__path__, __name__)

# Expose the canonical version so ``sage.__version__`` works.
from sage._version import __author__, __email__, __version__

__all__ = ["__version__", "__author__", "__email__"]
