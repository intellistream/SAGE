"""
Refiner Operator - SAGE RAG 算子
================================

统一的 Refiner 算子，用于在 SAGE 管道中进行上下文压缩。

架构:
    sage-libs (本文件): 提供 SAGE Function 适配器
    sage-middleware: 提供具体算法实现

用法:
    from sage.libs.rag.refiner import RefinerOperator

    config = {
        "algorithm": "long_refiner",  # 或 "simple", "none"
        "budget": 2048,
        "enable_cache": True,
        ...
    }

    env.map(RefinerOperator, config)
"""

import json
import os
import time
from typing import Any, Dict, List, Optional, Union

from sage.common.config.output_paths import get_states_file
from sage.kernel.api.function.map_function import MapFunction


class RefinerOperator(MapFunction):
    """
    Refiner 算子 - 用于 SAGE 管道中的上下文压缩

    委托给 sage.middleware.components.sage_refiner.RefinerService

    配置示例:
        config = {
            "algorithm": "long_refiner",  # 算法: long_refiner, simple, none
            "budget": 2048,               # token 预算
            "enable_cache": True,         # 启用缓存
            "enable_profile": False,      # 启用数据记录

            # LongRefiner 特定配置
            "base_model_path": "Qwen/Qwen2.5-3B-Instruct",
            "query_analysis_module_lora_path": "/path/to/lora/query",
            "doc_structuring_module_lora_path": "/path/to/lora/doc",
            "global_selection_module_lora_path": "/path/to/lora/global",
            "score_model_path": "BAAI/bge-reranker-v2-m3",
            ...
        }
    """

    def __init__(self, config: dict, ctx=None):
        super().__init__(config=config, ctx=ctx)
        self.cfg = config
        self.enable_profile = config.get("enable_profile", False)

        # 数据记录（仅当 enable_profile=True）
        if self.enable_profile:
            self.data_base_path = str(get_states_file("dummy", "refiner_data").parent)
            os.makedirs(self.data_base_path, exist_ok=True)
            self.data_records = []

        self._init_refiner()

    def _init_refiner(self):
        """初始化 Refiner 服务"""
        from sage.middleware.components.sage_refiner import RefinerService

        # 使用 middleware 的 RefinerService
        self.refiner_service = RefinerService(self.cfg)

        algorithm = self.cfg.get("algorithm", "long_refiner")
        self.logger.info(f"RefinerOperator initialized with algorithm: {algorithm}")

    def execute(self, data):
        """
        执行上下文压缩

        输入格式:
            dict: {"query": str, "retrieval_results": List[Dict], ...}
            或 dict: {"query": str, "retrieval_docs": List[str/Dict], ...}

        输出格式:
            dict: {
                ...原始字段,
                "refining_results": List[Dict],  # 压缩后的文档（结构化）
                "refining_docs": List[str],      # 压缩后的文本
            }
        """
        # 解析输入
        if isinstance(data, dict):
            query = data.get("query", "")
            # 优先级: reranking_results > refining_docs > retrieval_results > retrieval_docs > references
            docs = (
                data.get("reranking_results") or
                data.get("refining_docs") or
                data.get("retrieval_results") or
                data.get("retrieval_docs") or
                data.get("references", [])
            )
        else:
            self.logger.error(f"Unexpected input format: {type(data)}")
            return data

        # 标准化文档格式
        documents = self._normalize_documents(docs)

        # 调用 RefinerService
        try:
            result = self.refiner_service.refine(
                query=query,
                documents=documents,
                budget=self.cfg.get("budget"),
            )

            refined_texts = result.refined_content

        except Exception as e:
            self.logger.error(f"Refiner execution failed: {e}")
            refined_texts = [doc.get("text", str(doc)) for doc in documents]

        # 保存数据记录
        if self.enable_profile:
            self._save_data_record(query, documents, refined_texts)

        # 构造输出（使用统一字段名）
        if isinstance(data, dict):
            result_data = data.copy()
        else:
            result_data = {"query": query}

        result_data["refining_results"] = [{"text": text} for text in refined_texts]
        result_data["refining_docs"] = refined_texts

        return result_data

    def _normalize_documents(self, docs: List[Union[str, Dict]]) -> List[Dict]:
        """标准化文档格式"""
        normalized = []
        for doc in docs:
            if isinstance(doc, dict):
                # 提取文本
                text = doc.get("text") or doc.get("contents") or str(doc)

                # 添加标题（如果有）
                if "title" in doc and doc["title"]:
                    text = f"{doc['title']}\n{doc['title']} {text}"

                normalized_doc = {"text": text, **doc}
                
                # 保留 structured 字段（如果存在）
                if "structured" in doc:
                    normalized_doc["structured"] = doc["structured"]
                
                normalized.append(normalized_doc)
            elif isinstance(doc, str):
                normalized.append({"text": doc})
            else:
                normalized.append({"text": str(doc)})

        return normalized

    def _save_data_record(
        self, query: str, input_docs: List[Dict], refining_docs: List[str]
    ):
        """保存数据记录（仅当 enable_profile=True）"""
        if not self.enable_profile:
            return

        record = {
            "timestamp": time.time(),
            "query": query,
            "input_docs": input_docs,
            "refining_docs": refining_docs,
            "budget": self.cfg.get("budget"),
        }
        self.data_records.append(record)

        # 每10条记录持久化一次
        if len(self.data_records) >= 10:
            self._persist_data_records()

    def _persist_data_records(self):
        """持久化数据记录"""
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
        """确保数据被保存"""
        if hasattr(self, "enable_profile") and self.enable_profile:
            try:
                self._persist_data_records()
            except Exception:
                pass
