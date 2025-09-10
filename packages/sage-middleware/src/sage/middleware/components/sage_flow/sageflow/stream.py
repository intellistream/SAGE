"""
DataStream Python class wrapper for SAGE Flow.
Provides fluent API for stream processing.
"""

from typing import Callable, Any
from sageflow import DataStream as CppDataStream

class DataStream:
    def __init__(self, cpp_stream):
        self._stream = cpp_stream

    def map(self, func: Callable[[Any], Any]) -> 'DataStream':
        return DataStream(self._stream.map(func))

    def filter(self, func: Callable[[Any], bool]) -> 'DataStream':
        return DataStream(self._stream.filter(func))

    def source(self, src_func: Callable[[], Any]) -> 'DataStream':
        return DataStream(self._stream.source(src_func))

    def sink(self, sink_func: Callable[[Any], None]) -> 'DataStream':
        self._stream.sink(sink_func)
        return self

    def execute(self) -> Any:
        return self._stream.execute()

    def collect(self) -> Any:
        return self._stream.collect()