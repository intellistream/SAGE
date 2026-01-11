"""
Refiner Operator - SAGE RAG Pipeline Operator
==============================================

Uses isage-refiner (sage_refiner) for context compression in RAG pipelines.

Installation:
    pip install isage-refiner

Usage:
    from sage.middleware.operators.rag import RefinerOperator

    config = {
        "algorithm": "long_refiner",  # or "reform", "provence", etc.
        "budget": 2048,
        # LongRefiner specific
        "base_model_path": "Qwen/Qwen2.5-3B-Instruct",
        ...
    }

    env.map(RefinerOperator, config)
"""

import json
import os
import time
from typing import Any

from sage.common.config.output_paths import get_states_file
from sage.common.core.functions import MapFunction as MapOperator


class RefinerOperator(MapOperator):
    """
    Refiner Operator for SAGE RAG pipelines.

    Wraps isage-refiner compressors (LongRefiner, REFORM, Provence, etc.)
    for use in SAGE dataflow pipelines.

    Config:
        algorithm: str - "long_refiner", "reform", "provence", "llmlingua2", etc.
        budget: int - Token budget for compression
        enable_profile: bool - Enable data recording for debugging

        # Algorithm-specific config passed through to compressor
        base_model_path: str - For LongRefiner
        score_model_path: str - For LongRefiner
        ...
    """

    def __init__(self, config: dict, ctx=None):
        super().__init__(config=config, ctx=ctx)
        self.cfg = config
        self.enable_profile = config.get("enable_profile", False)
        self.compressor = None

        # Data recording (only when enable_profile=True)
        if self.enable_profile:
            self.data_base_path = str(get_states_file("dummy", "refiner_data").parent)
            os.makedirs(self.data_base_path, exist_ok=True)
            self.data_records: list[dict] = []

        self._init_compressor()

    def _init_compressor(self):
        """Initialize the compressor from isage-refiner."""
        algorithm = self.cfg.get("algorithm", "long_refiner").lower()

        try:
            if algorithm == "long_refiner":
                from sage_refiner import LongRefinerCompressor

                self.compressor = LongRefinerCompressor(
                    base_model_path=self.cfg.get("base_model_path", "Qwen/Qwen2.5-3B-Instruct"),
                    query_analysis_module_lora_path=self.cfg.get(
                        "query_analysis_module_lora_path", ""
                    ),
                    doc_structuring_module_lora_path=self.cfg.get(
                        "doc_structuring_module_lora_path", ""
                    ),
                    global_selection_module_lora_path=self.cfg.get(
                        "global_selection_module_lora_path", ""
                    ),
                    score_model_path=self.cfg.get("score_model_path", "BAAI/bge-reranker-v2-m3"),
                    max_model_len=self.cfg.get("max_model_len", 25000),
                    gpu_memory_utilization=self.cfg.get("gpu_memory_utilization", 0.5),
                )

            elif algorithm == "reform":
                from sage_refiner import REFORMCompressor

                self.compressor = REFORMCompressor(**self.cfg.get("reform_config", {}))

            elif algorithm == "provence":
                from sage_refiner import ProvenceCompressor

                self.compressor = ProvenceCompressor(**self.cfg.get("provence_config", {}))

            elif algorithm in ("simple", "none"):
                # Simple truncation - no compression
                self.compressor = None
                self.logger.info("Using simple/none mode - no compression")

            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")

            self.logger.info(f"RefinerOperator initialized with algorithm: {algorithm}")

        except ImportError as e:
            raise ImportError(
                f"Failed to import {algorithm} compressor. "
                f"Install with: pip install isage-refiner\n"
                f"Error: {e}"
            ) from e

    def execute(self, data: dict):
        """Execute document compression.

        Input format:
            {
                "query": str,
                "retrieval_results": List[Dict],  # Retrieved documents
            }

        Output format:
            {
                "query": str,
                "retrieval_results": List[Dict],  # Original (preserved)
                "refining_results": List[str],    # Compressed document texts
            }
        """
        if not isinstance(data, dict):
            self.logger.error(f"Unexpected input format: {type(data)}")
            return data

        query = data.get("query", "")
        docs = data.get("retrieval_results", [])

        # Normalize documents to isage-refiner format
        documents = self._normalize_documents(docs)

        # Compress
        try:
            if self.compressor is None:
                # Simple mode: just extract text
                refined_texts = [
                    doc.get("contents", doc.get("text", str(doc))) for doc in documents
                ]
            else:
                budget = self.cfg.get("budget", 2048)
                result = self.compressor.compress(
                    question=query,
                    document_list=documents,
                    budget=budget,
                )
                # isage-refiner returns dict with various fields
                refined_texts = result.get("compressed_context", "")
                if isinstance(refined_texts, str):
                    refined_texts = [refined_texts]

        except Exception as e:
            self.logger.error(f"Refiner execution failed: {e}")
            refined_texts = [doc.get("contents", str(doc)) for doc in documents]

        # Save data record if profiling
        if self.enable_profile:
            self._save_data_record(query, documents, refined_texts)

        # Build output
        result_data = data.copy()
        result_data["refining_results"] = refined_texts

        return result_data

    def _normalize_documents(self, docs: list[str | dict]) -> list[dict[str, Any]]:
        """Normalize documents to isage-refiner format (with 'contents' key)."""
        normalized: list[dict[str, Any]] = []
        for doc in docs:
            if isinstance(doc, dict):
                # isage-refiner expects 'contents' key
                text = doc.get("contents") or doc.get("text") or str(doc)
                normalized.append({"contents": text, **doc})
            elif isinstance(doc, str):
                normalized.append({"contents": doc})
            else:
                normalized.append({"contents": str(doc)})

        return normalized

    def _save_data_record(self, query: str, input_docs: list[dict], refined_docs: list[str]):
        """Save data record (only when enable_profile=True)."""
        if not self.enable_profile:
            return

        record = {
            "timestamp": time.time(),
            "query": query,
            "input_docs": input_docs,
            "refined_docs": refined_docs,
            "budget": self.cfg.get("budget"),
        }
        self.data_records.append(record)

        # Persist every 10 records
        if len(self.data_records) >= 10:
            self._persist_data_records()

    def _persist_data_records(self):
        """Persist data records to disk."""
        if not self.enable_profile or not self.data_records:
            return

        timestamp = int(time.time())
        filename = f"refiner_data_{timestamp}.json"
        path = os.path.join(self.data_base_path, filename)

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.data_records, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Saved {len(self.data_records)} records to {path}")
            self.data_records = []
        except Exception as e:
            self.logger.error(f"Failed to persist data records: {e}")

    def __del__(self):
        """Ensure data is saved on cleanup."""
        if hasattr(self, "enable_profile") and self.enable_profile:
            try:
                self._persist_data_records()
            except Exception:
                pass
