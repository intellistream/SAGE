"""
Refiner Operator - SAGE RAG 算子
================================

统一的 Refiner 算子，用于在 SAGE 管道中进行上下文压缩。

架构:
    sage-middleware (本文件): 提供 RAG 算子适配器
    sage-middleware/components/sage_refiner: 提供具体算法实现

用法:
    from sage.middleware.operators.rag import RefinerOperator

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
from typing import Any, cast

from sage.common.config.output_paths import get_states_file
from sage.common.core.functions import MapFunction as MapOperator


class RefinerOperator(MapOperator):
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

    def execute(self, data: dict):
        """执行文档压缩

        输入格式：
            {
                "query": str,
                "retrieval_results": List[Dict],  # 原始检索结果
            }

        输出格式：
            {
                "query": str,
                "retrieval_results": List[Dict],  # 原始检索结果（保留）
                "refining_results": List[str],    # 压缩后的文档文本
                "refine_time": float,             # 压缩耗时（由 MapOperator 自动添加）
            }
        """
        # 解析输入 - 只支持标准格式
        if not isinstance(data, dict):
            self.logger.error(f"Unexpected input format: {type(data)}")
            return data

        query = data.get("query", "")
        docs = data.get("retrieval_results", [])

        # 标准化文档格式
        documents = self._normalize_documents(docs)

        # 调用 RefinerService
        try:
            # Cast to satisfy type checker - documents are already normalized to dict format
            result = self.refiner_service.refine(
                query=query,
                documents=cast(list[str | dict[str, Any]], documents),
                budget=self.cfg.get("budget"),
            )

            refined_texts = result.refined_content

        except Exception as e:
            self.logger.error(f"Refiner execution failed: {e}")
            refined_texts = [doc.get("text", str(doc)) for doc in documents]

        # 保存数据记录
        if self.enable_profile:
            # Ensure refined_texts is a list of strings for data recording
            refined_list: list[str]
            if isinstance(refined_texts, str):
                refined_list = [refined_texts]
            elif isinstance(refined_texts, list):
                # refined_texts is already list[str] from RefineResult
                refined_list = refined_texts
            else:
                refined_list = [str(refined_texts)]
            self._save_data_record(query, documents, refined_list)

        # 构造输出
        result_data = data.copy()
        result_data["refining_results"] = refined_texts  # 压缩后的文档

        return result_data

    def _normalize_documents(self, docs: list[str | dict]) -> list[dict[str, Any]]:
        """标准化文档格式"""
        normalized: list[dict[str, Any]] = []
        for doc in docs:
            if isinstance(doc, dict):
                # 提取文本
                text = doc.get("text") or doc.get("contents") or str(doc)

                # 添加标题（如果有）
                if "title" in doc and doc["title"]:
                    text = f"{doc['title']}\n{doc['title']} {text}"

                normalized.append({"text": text, **doc})
            elif isinstance(doc, str):
                normalized.append({"text": doc})
            else:
                normalized.append({"text": str(doc)})

        return normalized

    def _save_data_record(self, query: str, input_docs: list[dict], refined_docs: list[str]):
        """保存数据记录（仅当 enable_profile=True）"""
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
