"""
SAGE Flow - High-performance vector stream processing engine (Python side)

All Python-facing APIs for SAGE-Flow live under this module.
"""

from typing import Any

import numpy as np

try:
    # Prefer relative import when installed as a package
    from . import _sage_flow  # type: ignore
except ImportError:  # pragma: no cover - repo/local build fallback
    import ctypes
    import importlib
    import os
    import sys
    from pathlib import Path

    here = Path(__file__).resolve().parent
    candidates = [
        here,  # same directory as this file (editable install case)
        here / "build" / "lib",  # python dir local build
        here.parent / "build" / "lib",  # component-level build
        here.parent,  # compiled module copied next to python/
        here.parent / "build",  # build directory
        here.parent / "install",  # install directory
    ]

    # Allow explicit override so CI can point to installed location
    extra_paths = os.environ.get("SAGE_FLOW_LIBRARY_PATH")
    if extra_paths:
        for token in extra_paths.split(os.pathsep):
            token_path = Path(token.strip())
            if token_path and token_path.exists():
                candidates.append(token_path)

    # Add paths and try direct import
    for p in candidates:
        if p.exists() and str(p) not in sys.path:
            sys.path.insert(0, str(p))

    # Try to find the .so file directly
    _sage_flow = None
    for p in candidates:
        if p.exists():
            # Look for _sage_flow.*.so files
            so_files = list(p.glob("_sage_flow*.so"))
            if so_files:
                # Add this directory to sys.path if not already there
                if str(p) not in sys.path:
                    sys.path.insert(0, str(p))
                break

    # Ensure the native lib dependency is preloaded so dlopen can succeed
    lib_loaded = False
    lib_names = [
        "libsageflow.so",  # Linux
        "libsageflow.dylib",  # macOS
        "sageflow.dll",  # Windows
    ]

    for p in candidates:
        if not p.exists():
            continue
        for lib_name in lib_names:
            lib_path = p / lib_name
            if lib_path.exists():
                try:
                    ctypes.CDLL(str(lib_path))
                    lib_loaded = True
                    break
                except OSError:
                    continue
        if lib_loaded:
            break

    if not lib_loaded:
        # Some build layouts place the shared library one level deeper (e.g. install/lib)
        for p in candidates:
            if not p.exists():
                continue
            for child in p.rglob("libsageflow*.so"):
                try:
                    ctypes.CDLL(str(child))
                    lib_loaded = True
                    break
                except OSError:
                    continue
            if lib_loaded:
                break

    if _sage_flow is None:
        _sage_flow = importlib.import_module("_sage_flow")  # type: ignore


# Re-export C++ classes and enums
DataType = _sage_flow.DataType
VectorData = _sage_flow.VectorData
VectorRecord = _sage_flow.VectorRecord
Stream = _sage_flow.Stream
StreamEnvironment = _sage_flow.StreamEnvironment
SimpleStreamSource = _sage_flow.SimpleStreamSource


class SageFlow:
    def __init__(self, config: dict[str, Any] | None = None):
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

    def get_stream_snapshot(self) -> dict[str, Any]:
        return {
            "streams_count": len(self.streams),
            "config": self.config,
            "status": "active",
        }


def create_stream_engine(config: dict[str, Any] | None = None) -> SageFlow:
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
