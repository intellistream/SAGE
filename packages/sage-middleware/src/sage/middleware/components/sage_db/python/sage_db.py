"""
Python interface for SAGE Database.

This module provides a Python interface to the SAGE vector database.
"""


class SageDB:
    """
    SAGE Database Python interface.

    In minimal mode (without C++ extensions), this provides a placeholder
    implementation that raises appropriate errors.
    """

    def __init__(self, **kwargs):
        """Initialize SAGE Database."""
        # Check if C++ extension is available
        try:
            # Try to load the C++ extension
            import sage_ext.sage_db._sage_db_cpp

            self._impl = sage_ext.sage_db._sage_db_cpp.SageDB(**kwargs)
            self._has_cpp = True
        except ImportError:
            # C++ extension not available - minimal mode
            self._impl = None
            self._has_cpp = False
            raise RuntimeError(
                "SAGE Database C++ extension not available. "
                "Please use full installation mode for vector database features."
            )

    def add_documents(self, documents, embeddings=None):
        """Add documents to the database."""
        if not self._has_cpp:
            raise RuntimeError("C++ extension required for database operations")
        return self._impl.add_documents(documents, embeddings)

    def search(self, query, k=10):
        """Search for similar documents."""
        if not self._has_cpp:
            raise RuntimeError("C++ extension required for database operations")
        return self._impl.search(query, k)


__all__ = ["SageDB"]
