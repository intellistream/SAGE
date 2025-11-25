"""
LongRefiner Operator for SAGE Pipeline
=======================================

将LongRefiner压缩算法封装为SAGE MapOperator，用于RAG pipeline。
三阶段上下文压缩：Query Analysis, Document Structuring, Global Selection。
"""

import logging

from sage.common.core.functions import MapFunction as MapOperator

from .compressor import LongRefinerCompressor

logger = logging.getLogger(__name__)


class LongRefinerOperator(MapOperator):
    """LongRefiner Operator

    在RAG pipeline中使用LongRefiner算法压缩检索到的上下文。

    输入格式:
        {
            "query": str,
            "retrieval_results": List[dict],  # 检索到的文档
        }

    输出格式:
        {
            "query": str,
            "retrieval_results": List[dict],  # 原始文档（保留）
            "refining_results": List[str],    # 压缩后的文档列表
            "compressed_context": str,         # 压缩后的完整上下文
            "original_tokens": int,
            "compressed_tokens": int,
            "compression_rate": float,
        }
    """

    def __init__(self, config: dict, ctx=None):
        super().__init__(config=config, ctx=ctx)
        self.cfg = config
        self.enabled = config.get("enabled", True)

        if self.enabled:
            self._init_compressor()
            logger.info("LongRefiner Operator initialized")
        else:
            logger.info("LongRefiner disabled (baseline mode)")

    def _init_compressor(self):
        """初始化LongRefiner压缩器"""
        # 创建LongRefiner压缩器
        self.compressor = LongRefinerCompressor(
            base_model_path=self.cfg.get("base_model_path", "Qwen/Qwen2.5-3B-Instruct"),
            query_analysis_module_lora_path=self.cfg.get("query_analysis_module_lora_path", ""),
            doc_structuring_module_lora_path=self.cfg.get("doc_structuring_module_lora_path", ""),
            global_selection_module_lora_path=self.cfg.get("global_selection_module_lora_path", ""),
            score_model_name=self.cfg.get("score_model_name", "bge-reranker-v2-m3"),
            score_model_path=self.cfg.get("score_model_path", "BAAI/bge-reranker-v2-m3"),
            max_model_len=self.cfg.get("max_model_len", 25000),
            gpu_memory_utilization=self.cfg.get("gpu_memory_utilization", 0.5),
        )

        logger.info(
            f"LongRefiner Compressor initialized with base model: {self.cfg.get('base_model_path')}"
        )

    def execute(self, data: dict) -> dict:
        """执行压缩

        Args:
            data: 包含query和retrieval_results的字典

        Returns:
            添加了refining_results等压缩结果的字典
        """
        if not isinstance(data, dict):
            logger.error(f"Unexpected input format: {type(data)}")
            return data

        query = data.get("query", "")
        retrieval_results = data.get("retrieval_results", [])

        # Handle empty retrieval results
        if not retrieval_results:
            logger.warning(f"No retrieval results for query: '{query[:50]}...'")
            result_data = data.copy()
            result_data["refining_results"] = []
            result_data["compressed_context"] = ""
            result_data["original_tokens"] = 0
            result_data["compressed_tokens"] = 0
            result_data["compression_rate"] = 1.0
            return result_data

        if not self.enabled:
            # Baseline mode: use original retrieval_results as refining_results
            result_data = data.copy()
            # Extract text from retrieval results for refining_results
            docs_text = []
            for result in retrieval_results:
                if isinstance(result, dict):
                    text = result.get("text") or result.get("contents") or str(result)
                else:
                    text = str(result)
                docs_text.append(text)

            result_data["refining_results"] = docs_text
            logger.info("LongRefiner disabled - passing through original documents")
            return result_data

        # Prepare documents in expected format
        documents = []
        for result in retrieval_results:
            if isinstance(result, dict):
                # Use 'contents' if available, otherwise concatenate title + text
                if "contents" in result:
                    doc = {"contents": result["contents"]}
                elif "text" in result:
                    title = result.get("title", "")
                    text = result["text"]
                    doc = {"contents": f"{title}\n{text}" if title else text}
                else:
                    doc = {"contents": str(result)}
            else:
                doc = {"contents": str(result)}
            documents.append(doc)

        # Log input statistics
        logger.info(f"LongRefiner: Processing {len(documents)} documents, query: '{query[:50]}...'")

        try:
            # Get budget and ratio
            budget = self.cfg.get("budget", 2048)
            ratio = self.cfg.get("compression_ratio", None)

            # Compress (time will be measured by MapOperator)
            compress_result = self.compressor.compress(
                question=query,
                document_list=documents,
                budget=budget,
                ratio=ratio,
            )

            compressed_text = compress_result["compressed_context"]
            refined_docs = compress_result["refined_docs"]
            original_tokens = compress_result["original_tokens"]
            compressed_tokens = compress_result["compressed_tokens"]
            compression_rate = compress_result["compression_rate"]

            # Log compression results
            logger.info(
                f"LongRefiner Compression: {original_tokens} → {compressed_tokens} tokens "
                f"({compression_rate:.1%})"
            )
            logger.debug(f"Compressed text preview: {compressed_text[:200]}...")

            # Build result - use refining_results for promptor
            result_data = data.copy()
            result_data["refining_results"] = refined_docs  # List of refined document strings
            result_data["compressed_context"] = compressed_text
            result_data["original_tokens"] = original_tokens
            result_data["compressed_tokens"] = compressed_tokens
            result_data["compression_rate"] = compression_rate

            return result_data

        except Exception as e:
            logger.error(f"LongRefiner compression failed: {e}", exc_info=True)
            # Fallback: return original documents
            result_data = data.copy()
            docs_text = [doc.get("contents", str(doc)) for doc in documents]
            result_data["refining_results"] = docs_text
            result_data["compressed_context"] = "\n\n".join(docs_text)
            return result_data
