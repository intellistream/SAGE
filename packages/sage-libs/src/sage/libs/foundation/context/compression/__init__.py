"""Context compression - MIGRATED to isage-refiner.

All context compression algorithms have been migrated to the independent package:

    pip install isage-refiner

Usage:
    from sage_refiner import LongRefinerCompressor, REFORMCompressor, ProvenceCompressor

    compressor = LongRefinerCompressor()
    result = compressor.compress(question, documents, budget=2048)

For SAGE middleware integration, see sage-middleware documentation.

This module is kept as a placeholder for backwards compatibility documentation.
No functionality remains here - use isage-refiner directly.
"""

__all__: list[str] = []
