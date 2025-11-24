"""
REFORM Compression Operator for SAGE Pipeline
==============================================

将REFORM压缩算法封装为SAGE MapOperator，用于RAG pipeline。
基于头选择的token级压缩算法。
"""

import logging

from sage.common.core.functions import MapFunction as MapOperator
from sage.middleware.components.sage_refiner.python.algorithms.reform.compressor import (
    REFORMCompressor,
)
from sage.middleware.components.sage_refiner.python.algorithms.reform.model_utils import (
    AttentionHookExtractor,
)

logger = logging.getLogger(__name__)


class REFORMRefinerOperator(MapOperator):
    """REFORM Refiner算子

    在RAG pipeline中使用REFORM算法压缩检索到的上下文。

    输入格式:
        {
            "query": str,
            "retrieval_results": List[str],  # 检索到的文档
        }

    输出格式:
        {
            "query": str,
            "retrieval_results": List[str],  # 原始文档（保留）
            "compressed_context": str,        # 压缩后的上下文
            "original_tokens": int,
            "compressed_tokens": int,
            "compression_rate": float,
            "num_spans": int,
        }
    """

    def __init__(self, config: dict, ctx=None):
        super().__init__(config=config, ctx=ctx)
        self.cfg = config
        self.enabled = config.get("enabled", True)

        if self.enabled:
            self._init_compressor()
            logger.info("REFORM Compression Operator initialized")
        else:
            logger.info("REFORM Compression disabled (baseline mode)")

    def _init_compressor(self):
        """初始化REFORM压缩器"""
        import torch

        # 1. 直接创建AttentionHookExtractor
        model_path = self.cfg.get("model_path")
        if not model_path:
            raise ValueError("model_path is required in reform config")

        selected_heads = self.cfg.get("selected_heads")
        if not selected_heads:
            raise ValueError("selected_heads is required in reform config")

        # 获取device
        device = self.cfg.get("device", "cuda" if torch.cuda.is_available() else "cpu")

        # 获取layer_range
        layer_range = self.cfg.get("layer_range")
        if layer_range:
            layer_range = tuple(layer_range)

        self.model_extractor = AttentionHookExtractor(
            model_name=model_path,
            device=device,
            dtype=self.cfg.get("dtype", "bfloat16"),
            use_flash_attention=self.cfg.get("use_flash_attention", False),
            layer_range=layer_range,
            cache_dir=self.cfg.get("cache_dir"),
        )

        # Register hooks
        self.model_extractor.register_hooks()

        logger.info(f"Loaded model: {model_path} on {device}")

        # 2. Get chunking config
        chunking_cfg = self.cfg.get("chunking", {})
        enable_chunking = chunking_cfg.get("enable", True)
        chunk_size = chunking_cfg.get("chunk_size")  # None for auto-calculate
        question_reserve = chunking_cfg.get("question_reserve", 200)
        margin = chunking_cfg.get("margin", 56)

        # 3. Create compressor with chunking support
        self.compressor = REFORMCompressor(
            model_extractor=self.model_extractor,
            selected_heads=selected_heads,
            max_tokens=self.cfg.get("max_tokens", 2048),
            keep_prefix=self.cfg.get("keep_prefix", 50),
            keep_suffix=self.cfg.get("keep_suffix", 50),
            smoothing_window=self.cfg.get("smoothing_window", 20),
            merge_threshold=self.cfg.get("merge_threshold", 5),
            use_kv_cache=self.cfg.get("use_kv_cache", True),
            enable_chunking=enable_chunking,
            chunk_size=chunk_size,
            question_reserve=question_reserve,
            margin=margin,
        )

        logger.info(f"REFORM Compressor initialized with {len(selected_heads)} selected heads")
        logger.info(f"Chunking mode: {'enabled' if enable_chunking else 'disabled'}")

    def execute(self, data: dict) -> dict:
        """执行压缩

        Args:
            data: 包含query和retrieval_results的字典

        Returns:
            添加了refining_results等压缩结果的字典
        """
        if not isinstance(data, dict):
            self.logger.error(f"Unexpected input format: {type(data)}")
            return data

        query = data.get("query", "")
        retrieval_results = data.get("retrieval_results", [])

        # Handle empty retrieval results
        if not retrieval_results:
            self.logger.warning(f"No retrieval results for query: '{query[:50]}...'")
            result_data = data.copy()
            result_data["refining_results"] = []
            result_data["compressed_context"] = ""
            result_data["original_tokens"] = 0
            result_data["compressed_tokens"] = 0
            result_data["compression_rate"] = 1.0
            result_data["num_spans"] = 0
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
            self.logger.info("REFORM disabled - passing through original documents")
            return result_data

        # Extract text from retrieval results
        docs_text = []
        for result in retrieval_results:
            if isinstance(result, dict):
                text = result.get("text") or result.get("contents") or str(result)
            else:
                text = str(result)
            docs_text.append(text)

        # Construct original context
        original_context = "\n\n".join(docs_text)

        # Log input statistics
        self.logger.info(f"REFORM: Processing {len(docs_text)} documents, query: '{query[:50]}...'")

        try:
            # Compress (time will be measured by MapOperator)
            compress_result = self.compressor.compress(
                context=original_context,
                question=query,
            )

            compressed_text = compress_result["compressed_context"]
            original_tokens = compress_result["original_tokens"]
            compressed_tokens = compress_result["compressed_tokens"]
            compression_rate = compress_result["compression_rate"]
            num_spans = compress_result["num_spans"]

            # Log compression results
            self.logger.info(
                f"REFORM Compression: {original_tokens} → {compressed_tokens} tokens "
                f"({compression_rate:.1%}), {num_spans} spans"
            )
            self.logger.debug(f"Compressed text preview: {compressed_text[:200]}...")

            # Build result - use refining_results for promptor
            result_data = data.copy()
            result_data["refining_results"] = [compressed_text]  # Promptor expects list
            result_data["compressed_context"] = compressed_text
            result_data["original_tokens"] = original_tokens
            result_data["compressed_tokens"] = compressed_tokens
            result_data["compression_rate"] = compression_rate
            result_data["num_spans"] = num_spans

            return result_data

        except Exception as e:
            self.logger.error(f"REFORM Compression failed: {e}", exc_info=True)
            # Fallback: use original documents as refining_results
            result_data = data.copy()
            result_data["refining_results"] = docs_text
            result_data["compressed_context"] = original_context
            result_data["original_tokens"] = 0
            result_data["compressed_tokens"] = 0
            result_data["compression_rate"] = 1.0
            result_data["num_spans"] = len(docs_text)
            self.logger.warning("Fallback to original documents due to compression error")
            return result_data
