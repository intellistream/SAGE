"""
Node Registry - Maps Studio UI node types to SAGE Operators
"""

import re

from sage.kernel.operators import MapOperator


def convert_node_type_to_snake_case(node_type: str) -> str:
    """
    将节点类型从 PascalCase 或 camelCase 转换为 snake_case

    Examples:
        TerminalSink -> terminal_sink
        FileSource -> file_source
        HFGenerator -> hf_generator
        OpenAIGenerator -> openai_generator
    """
    # 处理连续大写字母（如 HF, AI）
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", node_type)
    # 处理普通驼峰
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


class NodeRegistry:
    """Node Registry - Mapping from Studio UI node types to SAGE Operator classes"""

    def __init__(self):
        """Initialize Registry and register all available node types"""
        self._registry: dict[str, type[MapOperator]] = {}
        self._register_default_operators()

    def _register_default_operators(self):
        """Register default Operator mappings"""

        # Generic map operator
        self._registry["map"] = MapOperator

        # RAG Generators
        try:
            from sage.middleware.operators.rag import HFGenerator, OpenAIGenerator

            self._registry["openai_generator"] = OpenAIGenerator
            self._registry["hf_generator"] = HFGenerator
            self._registry["generator"] = OpenAIGenerator  # Default generator
        except ImportError:
            pass

        # RAG Retrievers
        try:
            from sage.middleware.operators.rag import (
                ChromaRetriever,
                MilvusDenseRetriever,
                MilvusSparseRetriever,
            )

            self._registry["chroma_retriever"] = ChromaRetriever
            self._registry["milvus_dense_retriever"] = MilvusDenseRetriever
            self._registry["milvus_sparse_retriever"] = MilvusSparseRetriever
            self._registry["retriever"] = ChromaRetriever  # Default retriever
        except ImportError:
            pass

        # RAG Rerankers
        try:
            from sage.middleware.operators.rag import BGEReranker

            self._registry["bge_reranker"] = BGEReranker
            self._registry["reranker"] = BGEReranker  # Default reranker
        except ImportError:
            pass

        # RAG Promptors
        try:
            from sage.middleware.operators.rag import QAPromptor, SummarizationPromptor

            self._registry["qa_promptor"] = QAPromptor
            self._registry["summarization_promptor"] = SummarizationPromptor
            self._registry["promptor"] = QAPromptor  # Default promptor
        except ImportError:
            pass

        # Document Processing
        try:
            from sage.middleware.operators.rag import CharacterSplitter, RefinerOperator

            self._registry["character_splitter"] = CharacterSplitter
            self._registry["refiner"] = RefinerOperator
            self._registry["chunker"] = CharacterSplitter  # Default chunker
        except ImportError:
            pass

        # Evaluation Operators
        try:
            from sage.middleware.operators.rag import (
                AccuracyEvaluate,
                F1Evaluate,
                RecallEvaluate,
            )

            self._registry["f1_evaluate"] = F1Evaluate
            self._registry["recall_evaluate"] = RecallEvaluate
            self._registry["accuracy_evaluate"] = AccuracyEvaluate
            self._registry["evaluator"] = F1Evaluate  # Default evaluator
        except ImportError:
            pass

        # Source Operators (用于 Pipeline 构建，但不作为 MapOperator 验证)
        try:
            from sage.libs.io.source import (
                CSVFileSource,
                FileSource,
                JSONFileSource,
                TextFileSource,
            )

            # 注册为特殊类型，PipelineBuilder 会特殊处理
            self._registry["file_source"] = FileSource  # type: ignore
            self._registry["csv_file_source"] = CSVFileSource  # type: ignore
            self._registry["json_file_source"] = JSONFileSource  # type: ignore
            self._registry["text_file_source"] = TextFileSource  # type: ignore
        except ImportError as e:
            print(f"Warning: Could not import Source operators: {e}")

        # Sink Operators (用于 Pipeline 构建，但不作为 MapOperator 验证)
        try:
            from sage.libs.io.sink import (
                FileSink,
                MemWriteSink,
                PrintSink,
                TerminalSink,
            )

            # 注册为特殊类型，PipelineBuilder 会特殊处理
            self._registry["print_sink"] = PrintSink  # type: ignore
            self._registry["terminal_sink"] = TerminalSink  # type: ignore
            self._registry["file_sink"] = FileSink  # type: ignore
            self._registry["mem_write_sink"] = MemWriteSink  # type: ignore
        except ImportError as e:
            print(f"Warning: Could not import Sink operators: {e}")

    def register(self, node_type: str, operator_class: type[MapOperator]):
        """Register a new node type"""
        self._registry[node_type] = operator_class

    def get_operator(self, node_type: str) -> type[MapOperator] | None:
        """Get the Operator class for a node type"""
        return self._registry.get(node_type)

    def list_types(self) -> list[str]:
        """List all registered node types"""
        return sorted(self._registry.keys())


# Singleton instance
_default_registry = None


def get_node_registry() -> NodeRegistry:
    """Get the default NodeRegistry instance (singleton pattern)"""
    global _default_registry
    if _default_registry is None:
        _default_registry = NodeRegistry()
    return _default_registry
