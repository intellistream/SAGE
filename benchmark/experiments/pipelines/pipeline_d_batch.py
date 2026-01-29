"""
Pipeline D: Batch Processing (批处理)
=====================================

拓扑: Source → Batch → Window → Future(LLM) → Aggregate → Sink

算子:
- Source: 加载数据流
- Map (Batch): 将数据分批
- Map (Window): 滑动/滚动窗口聚合
- Map (LLM): 批量 LLM 调用 (Future 语义)
- Sink (Aggregate): 聚合结果并输出

数据集: BBH, GPQA
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

# 禁用代理，确保内网服务可访问
os.environ.pop("http_proxy", None)
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("https_proxy", None)
os.environ.pop("HTTPS_PROXY", None)

import httpx

from sage.common.core import (
    MapFunction,
    SinkFunction,
    SourceFunction,
)
from sage.kernel.api import RemoteEnvironment

from .scheduler import HeadNodeScheduler


@dataclass
class BatchConfig:
    """Batch Pipeline 配置"""
    # 数据集
    dataset_name: str = "bbh"
    num_samples: int = 100

    # 批处理
    batch_size: int = 8
    window_size: int = 16

    # 模型
    llm_model: str = "Qwen/Qwen2.5-7B-Instruct"

    # 服务端点
    llm_base_url: str = "http://localhost:8001/v1"

    # 运行时
    job_manager_host: str = "localhost"
    job_manager_port: int = 19001
    request_timeout: float = 120.0


@dataclass
class BatchItem:
    """批处理数据项"""
    item_id: int
    query: str
    answer: str = ""
    batch_id: int = 0
    window_id: int = 0


# ============================================================================
# Source: 数据加载
# ============================================================================


class BatchSourceFunction(SourceFunction):
    """Batch Source: 加载数据集"""

    def __init__(
        self,
        dataset_name: str = "bbh",
        num_samples: int = 100,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.dataset_name = dataset_name
        self.num_samples = num_samples
        self._data: list[BatchItem] = []
        self._index = 0
        self._loaded = False

    def _load_data(self) -> None:
        """加载数据集"""
        if self._loaded:
            return

        if self.dataset_name == "bbh":
            from sage.data.sources.bbh.dataloader import BBHDataLoader
            loader = BBHDataLoader()
        else:
            from sage.data.sources.gpqa.dataloader import GPQADataLoader
            loader = GPQADataLoader()

        raw_data = loader.load()

        for i, sample in enumerate(raw_data[: self.num_samples]):
            self._data.append(BatchItem(
                item_id=i,
                query=sample.get("question", sample.get("query", "")),
            ))

        self._loaded = True
        print(f"📂 Loaded {len(self._data)} samples from {self.dataset_name}")

    def execute(self, data: Any = None) -> Optional[BatchItem]:
        """返回下一个数据项"""
        self._load_data()

        if self._index >= len(self._data):
            return None

        item = self._data[self._index]
        self._index += 1
        return item


# ============================================================================
# Map (Batch): 分批处理
# ============================================================================


class BatchingMapFunction(MapFunction):
    """Map (Batch): 将数据分批"""

    def __init__(self, batch_size: int = 8, **kwargs):
        super().__init__(**kwargs)
        self.batch_size = batch_size
        self._buffer: list[BatchItem] = []
        self._batch_id = 0

    def execute(self, item: BatchItem) -> Optional[list[BatchItem]]:
        """执行分批"""
        item.batch_id = self._batch_id
        self._buffer.append(item)

        if len(self._buffer) >= self.batch_size:
            batch = self._buffer
            self._buffer = []
            self._batch_id += 1
            print(f"📦 Batch {item.batch_id}: {len(batch)} items")
            return batch

        return None


# ============================================================================
# Map (Window): 窗口聚合
# ============================================================================


class WindowMapFunction(MapFunction):
    """Map (Window): 窗口聚合"""

    def __init__(self, window_size: int = 16, **kwargs):
        super().__init__(**kwargs)
        self.window_size = window_size
        self._window_buffer: list[BatchItem] = []
        self._window_id = 0

    def execute(self, batch: Optional[list[BatchItem]]) -> Optional[list[BatchItem]]:
        """执行窗口聚合"""
        if batch is None:
            return None

        for item in batch:
            item.window_id = self._window_id
        self._window_buffer.extend(batch)

        if len(self._window_buffer) >= self.window_size:
            window = self._window_buffer
            self._window_buffer = []
            self._window_id += 1
            print(f"🪟 Window {window[0].window_id}: {len(window)} items")
            return window

        return None


# ============================================================================
# Map (LLM): 批量 LLM 调用
# ============================================================================


class BatchLLMMapFunction(MapFunction):
    """Map (LLM): 批量 LLM 调用"""

    def __init__(
        self,
        llm_base_url: str = "http://localhost:8001/v1",
        llm_model: str = "Qwen/Qwen2.5-7B-Instruct",
        timeout: float = 120.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.timeout = timeout

    def execute(self, window: Optional[list[BatchItem]]) -> Optional[list[BatchItem]]:
        """执行批量 LLM 调用"""
        if window is None:
            return None

        with httpx.Client(timeout=self.timeout) as client:
            for item in window:
                response = client.post(
                    f"{self.llm_base_url}/chat/completions",
                    json={
                        "model": self.llm_model,
                        "messages": [{"role": "user", "content": item.query}],
                        "max_tokens": 128,
                        "temperature": 0.7,
                    },
                )
                response.raise_for_status()
                result = response.json()
                item.answer = result["choices"][0]["message"]["content"]

        print(f"🤖 LLM processed {len(window)} items")
        return window


# ============================================================================
# Sink (Aggregate): 聚合结果
# ============================================================================


class BatchSinkFunction(SinkFunction):
    """Batch Sink: 聚合结果并输出"""

    def __init__(self, output_path: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.output_path = output_path
        self.results: list[dict] = []
        self.total_items = 0

    def execute(self, window: Optional[list[BatchItem]]) -> None:
        """输出结果"""
        if window is None:
            return

        for item in window:
            self.total_items += 1
            result = {
                "item_id": item.item_id,
                "query": item.query,
                "answer": item.answer,
                "batch_id": item.batch_id,
                "window_id": item.window_id,
            }
            self.results.append(result)
            print(f"✅ [{item.item_id}] Q: {item.query[:30]}... → A: {item.answer[:30]}...")

        if self.output_path:
            import json
            with open(self.output_path, "a") as f:
                for r in self.results[-len(window):]:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ============================================================================
# Batch Pipeline 封装
# ============================================================================


class BatchPipeline:
    """Batch Pipeline 封装类"""

    def __init__(self, config: BatchConfig):
        self.config = config
        self.env: Optional[RemoteEnvironment] = None

    def build(self) -> RemoteEnvironment:
        """构建 Batch Pipeline"""
        scheduler = HeadNodeScheduler()

        self.env = RemoteEnvironment(
            "batch_pipeline",
            host=self.config.job_manager_host,
            port=self.config.job_manager_port,
            scheduler=scheduler,
        )

        # 构建 Pipeline: Source → Map(Batch) → Map(Window) → Map(LLM) → Sink
        (
            self.env.from_source(
                BatchSourceFunction,
                dataset_name=self.config.dataset_name,
                num_samples=self.config.num_samples,
            )
            .map(BatchingMapFunction, batch_size=self.config.batch_size)
            .map(WindowMapFunction, window_size=self.config.window_size)
            .map(
                BatchLLMMapFunction,
                llm_base_url=self.config.llm_base_url,
                llm_model=self.config.llm_model,
                timeout=self.config.request_timeout,
            )
            .sink(BatchSinkFunction)
        )

        return self.env

    def run(self) -> dict:
        """运行 Pipeline"""
        if self.env is None:
            self.build()

        start_time = time.time()
        try:
            self.env.submit()
            time.sleep(15)  # 批处理需要更多时间
        finally:
            self.env.close()

        duration = time.time() - start_time
        return {
            "pipeline": "D (Batch)",
            "duration_seconds": duration,
            "config": {
                "dataset": self.config.dataset_name,
                "batch_size": self.config.batch_size,
                "window_size": self.config.window_size,
            },
        }
