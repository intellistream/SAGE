"""
SAGE Flow - High-performance vector stream processing engine (Python side)

All Python-facing APIs for SAGE-Flow live under this module.
"""

from typing import Any, Callable, Dict, Optional

import numpy as np

# Initialize to None first
_sage_flow = None

try:
    # Prefer relative import when installed as a package
    from . import _sage_flow  # type: ignore
except ImportError as import_err:  # pragma: no cover - repo/local build fallback
    import importlib
    import os
    import sys
    import warnings
    from pathlib import Path

    # Store the original error for debugging
    original_import_error = str(import_err)
    
    here = Path(__file__).resolve().parent
    candidate_paths = [
        here,  # same directory as this file (editable install case)
        here / "build" / "lib",  # standard local build
        here.parent / "build" / "lib",  # component-level build
        here.parent / "build",  # build directory
        here.parent / "install",  # install directory
    ]

    # Add paths to sys.path
    for p in candidate_paths:
        if p.exists() and str(p) not in sys.path:
            sys.path.insert(0, str(p))

    # Try to find the .so file directly
    found_so = False
    so_file_path = None
    for p in candidate_paths:
        if p.exists():
            # Look for _sage_flow.*.so files
            so_files = list(p.glob("_sage_flow*.so"))
            if so_files:
                found_so = True
                so_file_path = str(so_files[0])
                # Add this directory to sys.path if not already there
                if str(p) not in sys.path:
                    sys.path.insert(0, str(p))
                break

    # Import the module
    if found_so or _sage_flow is None:
        try:
            _sage_flow = importlib.import_module("_sage_flow")  # type: ignore
        except Exception as e:
            # Provide detailed error information - use print to ensure visibility
            import sys
            print(f"\n{'='*70}", file=sys.stderr)
            print(f"ERROR: Failed to import _sage_flow extension module", file=sys.stderr)
            print(f"{'='*70}", file=sys.stderr)
            print(f"Original import error: {original_import_error}", file=sys.stderr)
            print(f"Found .so file: {found_so}", file=sys.stderr)
            if so_file_path:
                print(f".so file path: {so_file_path}", file=sys.stderr)
            print(f"importlib.import_module error: {type(e).__name__}: {e}", file=sys.stderr)
            print(f"Searched paths: {[str(p) for p in candidate_paths if p.exists()]}", file=sys.stderr)
            print(f"sys.path (first 5): {sys.path[:5]}", file=sys.stderr)
            print(f"{'='*70}\n", file=sys.stderr)
            # Also issue a warning
            import warnings
            warnings.warn(
                f"_sage_flow extension not available. {type(e).__name__}: {e}",
                ImportWarning
            )
            # If import still fails, _sage_flow remains None
            pass

# Only define these if _sage_flow was successfully imported
if _sage_flow is not None:
    DataType = _sage_flow.DataType
    VectorData = _sage_flow.VectorData
    VectorRecord = _sage_flow.VectorRecord
    Stream = _sage_flow.Stream
    StreamEnvironment = _sage_flow.StreamEnvironment
    SimpleStreamSource = _sage_flow.SimpleStreamSource
else:
    # Provide stub definitions for when extension is not available
    import sys
    import warnings
    
    error_msg = (
        "\n" + "="*70 + "\n"
        "CRITICAL: _sage_flow C++ extension is not available!\n"
        "Stream processing features will NOT work.\n"
        "This usually means:\n"
        "  1. The extension was not built (run: sage extensions install sage_flow)\n"
        "  2. The .so file exists but has import errors (check stderr above)\n"
        "  3. Missing C++ dependencies or ABI incompatibility\n"
        + "="*70
    )
    print(error_msg, file=sys.stderr)
    warnings.warn(
        "_sage_flow extension not available. Stream processing features will be limited.",
        ImportWarning
    )
    
    DataType = None
    VectorData = None
    VectorRecord = None
    Stream = None
    StreamEnvironment = None
    SimpleStreamSource = None


class SageFlow:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.env = StreamEnvironment()
        self.streams = []
        self.config = config or {}

    def create_stream(self, name: str):
        return Stream(name)

    def create_simple_source(self, name: str):
        return SimpleStreamSource(name)

    def add_vector_record(self, source, uid: int, timestamp: int, vector):
        if isinstance(vector, np.ndarray):
            vector = vector.astype(np.float32, copy=False)
        else:
            vector = np.asarray(vector, dtype=np.float32)
        source.addRecord(uid, timestamp, vector)

    def add_stream(self, stream):
        self.streams.append(stream)
        self.env.addStream(stream)

    def execute(self):
        self.env.execute()

    def get_stream_snapshot(self) -> Dict[str, Any]:
        return {
            "streams_count": len(self.streams),
            "config": self.config,
            "status": "active",
        }


def create_stream_engine(config: Optional[Dict[str, Any]] = None) -> SageFlow:
    return SageFlow(config)


def create_vector_stream(name: str):
    return Stream(name)


def create_simple_data_source(name: str):
    return SimpleStreamSource(name)


__all__ = [
    "SageFlow",
    "create_stream_engine",
    "create_vector_stream",
    "create_simple_data_source",
    "DataType",
    "VectorData",
    "VectorRecord",
    "Stream",
    "StreamEnvironment",
    "SimpleStreamSource",
]
