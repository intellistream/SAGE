# sage/api/function/__init__.py

from .base import Function
from .registry import register_function, get_function

# 将 core 里的具体实现，再次在 API 里导出
from sage.core.function.source import FileSourceFunction as FileSource
from sage.core.function.retriever import SimpleRetrieverFunction as SimpleRetriever
from sage.core.function.promptor import QAPromptorFunction as QAPromptor
from sage.core.function.generator import OpenAIGeneratorFunction as OpenAIGenerator
from sage.core.function.sink import FileSinkFunction as FileSink

__all__ = [
    "Function",
    "register_function", "get_function",
    "FileSource", "SimpleRetriever", "QAPromptor", "OpenAIGenerator", "FileSink",
]
