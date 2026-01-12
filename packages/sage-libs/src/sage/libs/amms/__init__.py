"""AMMS - Approximate Matrix Multiplication (interface only in SAGE).

The **implementations have been migrated to an independent package**
(`isage-amms`, planned repo: ``intellistream/sage-amms``). SAGE now only ships the
lightweight interface/registry so downstream code can keep `from sage.libs.amms
import create` while the compiled extensions live in the external package.

Usage (after installing the external package):

    pip install isage-amms

    from sage.libs.amms import create
    amm = create("countsketch", sketch_size=1000)
    result = amm.multiply(matrix_a, matrix_b)

If the optional dependency is missing, attempting to instantiate algorithms will
raise a KeyError because no implementations are registered. This is intentional
to avoid silent fallbacks.
"""

__version__ = "0.1.0"
__author__ = "IntelliStream Team"
__email__ = "shuhao_zhang@hust.edu.cn"

# Import interface components
import warnings

from sage.libs.amms.interface import (
    AmmIndex,
    AmmIndexMeta,
    StreamingAmmIndex,
    create,
    get_meta,
    register,
    registered,
    unregister,
)

warnings.warn(
    "AMM implementations are being externalized to 'isage-amms'. Install the optional extra "
    "[amms] or add 'isage-amms' to your environment to access concrete algorithms.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    # Base classes
    "AmmIndex",
    "AmmIndexMeta",
    "StreamingAmmIndex",
    # Factory functions
    "create",
    "registered",
    "get_meta",
    # Registry functions
    "register",
    "unregister",
]
