"""
Batch Processing Functions for HuggingFace Datasets

This module provides batch processing functions for loading data from
HuggingFace datasets, with specialized subclasses for different benchmarks.

Hierarchy:
- HFDatasetBatch: Base class for HuggingFace dataset loading
  - FlashRAGBatch: FlashRAG benchmark (question/golden_answers fields)
  - LongBenchBatch: LongBench benchmark (input/context/answers fields)
"""

import json
import os
from typing import Any

from sage.common.core import BatchFunction, StopSignal

try:
    from datasets import load_dataset

    HAS_DATASETS = True
except ImportError:
    HAS_DATASETS = False


class HFDatasetBatch(BatchFunction):
    """
    HuggingFace数据集批处理基类

    从HuggingFace数据集中批量读取数据，支持流式处理。
    当数据集处理完成时返回 StopSignal 来停止批处理。

    这是一个抽象基类，子类需要实现 _transform_example() 方法来定义
    如何将原始数据集字段映射到 SAGE RAG 标准字段。

    Input: None (直接从HF数据集读取)
    Output: 由子类 _transform_example() 定义的字典对象

    Attributes:
        config: 配置字典，包含数据集设置
        hf_name: HuggingFace数据集名称
        hf_config: 数据集配置名称
        hf_split: 数据集分割（train/validation/test等）
        max_samples: 最大样本数限制
        _iter: 数据集迭代器
        _dataset_exhausted: 数据集是否已耗尽
        _sample_count: 已处理样本计数

    Config Keys:
        hf_dataset_name: str - HuggingFace数据集名称（必需）
        hf_dataset_config: str - 数据集配置名称（可选）
        hf_split: str - 数据集分割，默认 "train"
        max_samples: int - 最大样本数限制（可选）
    """

    def __init__(self, config: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        if not HAS_DATASETS:
            raise ImportError(
                "datasets library is required for HFDatasetBatch. Install with: pip install datasets"
            )
        if config is None:
            raise ValueError("config is required for HFDatasetBatch")
        self.config = config
        self.hf_name = config["hf_dataset_name"]
        self.hf_config = config.get("hf_dataset_config")
        self.hf_split = config.get("hf_split", "train")
        self.max_samples = config.get("max_samples", None)
        self._iter = None
        self._dataset_exhausted = False
        self._sample_count = 0

        # Log configuration
        if self.max_samples is not None:
            self.logger.info(
                f"{self.__class__.__name__} configured with max_samples={self.max_samples}"
            )
        else:
            self.logger.info(f"{self.__class__.__name__}: no max_samples limit")

    def _transform_example(self, ex: dict[str, Any]) -> dict[str, Any]:
        """
        将原始数据集样本转换为 SAGE RAG 标准格式

        子类必须实现此方法，定义字段映射逻辑。

        Args:
            ex: 原始数据集样本（dict-like）

        Returns:
            dict: 转换后的样本，应包含 SAGE RAG 标准字段
                  （query, references, context, results 等）
        """
        raise NotImplementedError("Subclasses must implement _transform_example()")

    def _build_iter(self):
        """构建数据集迭代器"""
        ds = load_dataset(
            self.hf_name,
            self.hf_config,
            split=self.hf_split,
            streaming=True,
            trust_remote_code=True,
        )
        for ex in ds:
            if isinstance(ex, dict):
                yield self._transform_example(ex)

    def execute(self):
        """
        执行批处理函数逻辑

        Returns:
            dict: 转换后的数据字典
            StopSignal: 数据集结束时返回StopSignal
        """
        if self._dataset_exhausted:
            return StopSignal(f"{self.__class__.__name__}-exhausted")

        # Check if we've reached max_samples limit
        if self.max_samples is not None and self._sample_count >= self.max_samples:
            self.logger.info(
                f"Reached max_samples limit ({self.max_samples}), stopping batch processing"
            )
            self._dataset_exhausted = True
            return StopSignal(f"{self.__class__.__name__}-max_samples-{self.max_samples}")

        if self._iter is None:
            self.logger.debug(f"Initializing HF dataset batch source: {self.hf_name}")
            if self.max_samples:
                self.logger.info(f"Will process up to {self.max_samples} samples")
            self._iter = self._build_iter()

        try:
            data = next(self._iter)
            self._sample_count += 1
            self.logger.debug(
                f"Yielding batch data ({self._sample_count}"
                + (f"/{self.max_samples}" if self.max_samples else "")
                + f"): query={data.get('query', '')[:50]}..."
            )
            return data
        except StopIteration:
            self.logger.info(f"HF dataset batch processing completed for: {self.hf_name}")
            self._dataset_exhausted = True
            return StopSignal(f"{self.__class__.__name__}-completed")


class FlashRAGBatch(HFDatasetBatch):
    """
    FlashRAG 数据集批处理函数

    专门用于 FlashRAG 基准测试数据集，字段映射：
    - question → query
    - golden_answers → references

    Input: None (直接从HF数据集读取)
    Output: {"query": str, "references": List[str], "results": []}

    Config Keys (继承自 HFDatasetBatch):
        hf_dataset_name: str - 如 "RUC-NLPIR/FlashRAG_datasets"
        hf_dataset_config: str - 如 "nq", "triviaqa" 等
        hf_split: str - 默认 "train"
        max_samples: int - 最大样本数限制
    """

    def _transform_example(self, ex: dict[str, Any]) -> dict[str, Any]:
        """FlashRAG 字段映射: question → query, golden_answers → references"""
        return {
            "query": ex.get("question", ""),
            "references": ex.get("golden_answers") or [],
            "results": [],  # FlashRAG 需要检索，初始为空
        }


class LongBenchBatch(HFDatasetBatch):
    """
    LongBench 数据集批处理函数

    专门用于 LongBench 长文本理解基准测试，字段映射：
    - input → query（用户问题）
    - context → context（长文本上下文，LongBench 自带，无需检索）
    - answers → references（标准答案列表）
    - all_classes → all_classes（分类任务的类别列表）
    - length → length（原始文本长度，用于 LongBench-E 分桶评估）

    **与 SAGE RAG Pipeline 的对齐说明**：

    SAGE RAG 标准数据流:
    - query: 用户问题
    - references: 标准答案（评估用）
    - retrieval_results: 检索到的文档 List[Dict]（Retriever 输出）
    - refining_results: 压缩后的文档 List[str]（Refiner 输出）
    - context: 上下文字符串或列表（Promptor 读取）
    - generated: 生成的答案（Generator 输出）

    LongBench 特殊处理:
    - LongBench 自带 context，跳过 Retriever 阶段
    - context 直接作为 `context` 字段供 Promptor 使用
    - 同时设置 `retrieval_results` 为空列表（表示无检索）

    Input: None (直接从HF数据集读取)
    Output: SAGE RAGResponse 兼容格式 + LongBench 专用字段

    Config Keys (继承自 HFDatasetBatch):
        hf_dataset_name: str - 固定为 "THUDM/LongBench"
        hf_dataset_config: str - 如 "multi_news", "hotpotqa", "multi_news_e" 等
        hf_split: str - 默认 "test"
        max_samples: int - 最大样本数限制

    Output Fields (SAGE RAG 标准字段):
        query: str - 用户问题（来自 LongBench input）
        references: List[str] - 标准答案列表（来自 LongBench answers，评估用）
        context: str - 长文本上下文（来自 LongBench context，供 Promptor 使用）
        retrieval_results: List[Dict] - 空列表（LongBench 不走检索）

    Output Fields (LongBench 专用字段):
        all_classes: List[str] | None - 分类任务类别（trec, lsht 等）
        length: int - 原始文本长度（LongBench-E 分桶评估用）
        _dataset: str - 数据集名称（用于选择评估指标）
        _is_longbench_e: bool - 是否是 LongBench-E 版本
    """

    def __init__(self, config: dict | None = None, **kwargs):
        super().__init__(config, **kwargs)
        # 解析数据集名称和是否为 LongBench-E
        self._dataset_name = self._parse_dataset_name()
        self._is_longbench_e = self._check_longbench_e()

    def _parse_dataset_name(self) -> str:
        """从 hf_dataset_config 解析数据集名称（去除 _e 后缀）"""
        config_name = self.hf_config or ""
        if config_name.endswith("_e"):
            return config_name[:-2]  # 去除 _e 后缀
        return config_name

    def _check_longbench_e(self) -> bool:
        """检查是否是 LongBench-E 版本"""
        config_name = self.hf_config or ""
        return config_name.endswith("_e")

    def _transform_example(self, ex: dict[str, Any]) -> dict[str, Any]:
        """
        LongBench 字段映射到 SAGE RAG Pipeline 标准格式

        LongBench 原始字段 → SAGE RAG 标准字段:
        - input → query（用户问题）
        - context → context（上下文，供 Promptor 使用）
        - answers → references（标准答案，供 Evaluate 使用）

        LongBench 专用字段保留:
        - all_classes（分类任务类别）
        - length（原始长度，LongBench-E 分桶用）
        """
        return {
            # ========== SAGE RAG Pipeline 标准字段 ==========
            "query": ex.get("input", ""),
            "references": ex.get("answers") or [],
            "context": ex.get("context", ""),
            # 空列表表示跳过检索阶段（LongBench 自带 context）
            "retrieval_results": [],
            # ========== LongBench 专用字段 ==========
            "all_classes": ex.get("all_classes"),
            "length": ex.get("length", 0),
            # ========== 内部元数据（下划线前缀，pipeline 流转用）==========
            "_dataset": self._dataset_name,
            "_is_longbench_e": self._is_longbench_e,
        }


class JSONLBatch(BatchFunction):
    """
    JSONL文件批处理函数

    逐行读取JSONL文件中的数据，支持流式处理。
    当文件处理完成时返回None来停止批处理。

    Input: None (直接从JSONL文件读取)
    Output: 包含query和其他字段的字典对象

    Attributes:
        config: 配置字典，包含文件路径设置
        file_path: JSONL文件路径
        _file_handle: 文件句柄
        _file_exhausted: 文件是否已读取完毕
    """

    def __init__(self, config: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        if config is None:
            raise ValueError("config is required for JsonlFileBatch")
        self.config = config
        self.file_path = config["data_path"]
        self._file_handle = None
        self._file_exhausted = False

    def _open_file(self):
        """打开JSONL文件"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"JSONL file not found: {self.file_path}")

        self._file_handle = open(self.file_path, encoding="utf-8")
        self.logger.debug(f"Opened JSONL file: {self.file_path}")

    def execute(self):
        """
        执行批处理函数逻辑

        Returns:
            dict: 包含query和其他字段的数据字典
            StopSignal: 文件结束时返回StopSignal
        """
        if self._file_exhausted:
            return StopSignal("JSONLBatch-exhausted")

        if self._file_handle is None:
            self.logger.debug(f"Initializing JSONL batch source: {self.file_path}")
            self._open_file()

        assert self._file_handle is not None, "File handle should be initialized"

        try:
            line = self._file_handle.readline()
            if not line:
                # 文件读取完毕
                self.logger.info(f"JSONL file batch processing completed for: {self.file_path}")
                self._file_handle.close()
                self._file_exhausted = True
                return StopSignal("JSONLBatch-completed")

            # 解析JSON行
            line = line.strip()
            if line:
                data = json.loads(line)
                # 如果data包含query字段，直接返回query字符串
                if "query" in data:
                    query_text = data["query"]
                    self.logger.debug(f"Yielding JSONL query: {query_text}")
                    return query_text
                else:
                    # 否则返回完整数据
                    self.logger.debug(f"Yielding JSONL data: {data}")
                    return data
            else:
                # 空行，继续读取下一行
                return self.execute()

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON line: {line}, error: {e}")
            # 跳过错误行，继续处理
            return self.execute()
        except Exception as e:
            self.logger.error(f"Error reading JSONL file: {e}")
            if self._file_handle:
                self._file_handle.close()
            self._file_exhausted = True
            return StopSignal(f"JSONLBatch-error-{str(e)}")

    def __del__(self):
        """析构函数，确保文件句柄被正确关闭"""
        if hasattr(self, "_file_handle") and self._file_handle:
            self._file_handle.close()
