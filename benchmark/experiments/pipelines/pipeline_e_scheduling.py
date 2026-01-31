"""
Pipeline E: Priority Scheduling (优先级调度)
============================================

拓扑: Source×3 → KeyBy(Scheduler) → Batch → Future(LLM) → Sink

算子:
- Source×3: 不同优先级的请求源 (High, Medium, Low)
- Map (KeyBy/Scheduler): 根据优先级调度
- Map (Batch): 按优先级分批
- Map (LLM): LLM 调用 (Future 语义)
- Sink: 结果输出 + SLO 统计

调度策略:
- FIFO: 先进先出
- Priority: 高优先级优先
- SLO-Aware: 优先处理即将违约的请求
- Hybrid: 综合优先级和 SLO 紧迫度
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import httpx

from sage.common.core import (
    MapFunction,
    SinkFunction,
    SourceFunction,
)
from sage.kernel.api import RemoteEnvironment

from .scheduler import HeadNodeScheduler


class SchedulerType(str, Enum):
    """调度器类型"""

    FIFO = "fifo"
    PRIORITY = "priority"
    SLO_AWARE = "slo_aware"
    HYBRID = "hybrid"


class RequestPriority(str, Enum):
    """请求优先级"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SchedulingConfig:
    """Scheduling Pipeline 配置"""

    # 请求配置
    num_requests: int = 200
    high_priority_ratio: float = 0.2
    medium_priority_ratio: float = 0.5
    low_priority_ratio: float = 0.3

    # SLO 目标
    high_priority_slo_ms: float = 500.0
    medium_priority_slo_ms: float = 1000.0
    low_priority_slo_ms: float = 2000.0

    # 调度策略
    scheduler_type: SchedulerType = SchedulerType.HYBRID

    # 批处理
    batch_size: int = 8

    # 模型
    llm_model: str = "Qwen/Qwen2.5-7B-Instruct"

    # 服务端点
    llm_base_url: str = "http://localhost:8001/v1"

    # 运行时
    job_manager_host: str = "localhost"
    job_manager_port: int = 19001
    request_timeout: float = 60.0


@dataclass
class SchedulingRequest:
    """调度请求"""

    request_id: str
    priority: RequestPriority
    slo_target_ms: float
    query: str
    arrival_time_ms: float
    answer: str = ""
    completion_time_ms: float = 0.0

    @property
    def latency_ms(self) -> float:
        if self.completion_time_ms == 0:
            return 0.0
        return self.completion_time_ms - self.arrival_time_ms

    @property
    def slo_met(self) -> bool:
        return self.latency_ms <= self.slo_target_ms


# ============================================================================
# Source: 多优先级请求源
# ============================================================================


class SchedulingSourceFunction(SourceFunction):
    """Scheduling Source: 生成不同优先级的请求"""

    def __init__(
        self,
        num_requests: int = 200,
        high_priority_ratio: float = 0.2,
        medium_priority_ratio: float = 0.5,
        low_priority_ratio: float = 0.3,
        high_priority_slo_ms: float = 500.0,
        medium_priority_slo_ms: float = 1000.0,
        low_priority_slo_ms: float = 2000.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.num_requests = num_requests
        self.high_ratio = high_priority_ratio
        self.medium_ratio = medium_priority_ratio
        self.low_ratio = low_priority_ratio
        self.high_slo = high_priority_slo_ms
        self.medium_slo = medium_priority_slo_ms
        self.low_slo = low_priority_slo_ms
        self._index = 0
        self._base_time = time.time() * 1000

    def execute(self, data: Any = None) -> Optional[SchedulingRequest]:
        """返回下一个请求"""
        if self._index >= self.num_requests:
            return None

        i = self._index
        self._index += 1

        # 确定性分配优先级
        segment = i % 10
        high_threshold = int(self.high_ratio * 10)
        medium_threshold = high_threshold + int(self.medium_ratio * 10)

        if segment < high_threshold:
            priority = RequestPriority.HIGH
            slo = self.high_slo
        elif segment < medium_threshold:
            priority = RequestPriority.MEDIUM
            slo = self.medium_slo
        else:
            priority = RequestPriority.LOW
            slo = self.low_slo

        return SchedulingRequest(
            request_id=f"req_{i:04d}",
            priority=priority,
            slo_target_ms=slo,
            query=f"Answer briefly: What is {i} times 2?",
            arrival_time_ms=self._base_time + i * 10,
        )


# ============================================================================
# Map (Scheduler): 调度器
# ============================================================================


class SchedulerMapFunction(MapFunction):
    """Map (Scheduler): 根据策略调度请求"""

    def __init__(self, scheduler_type: str = "hybrid", batch_size: int = 8, **kwargs):
        super().__init__(**kwargs)
        self.scheduler_type = scheduler_type
        self.batch_size = batch_size
        self._queue: list[SchedulingRequest] = []

    def execute(self, request: SchedulingRequest) -> Optional[list[SchedulingRequest]]:
        """执行调度"""
        self._queue.append(request)

        if len(self._queue) >= self.batch_size:
            # 根据策略排序
            batch = self._schedule_batch()
            print(f"📋 Scheduled batch: {[r.priority.value for r in batch]}")
            return batch

        return None

    def _schedule_batch(self) -> list[SchedulingRequest]:
        """根据策略调度批次"""
        batch = self._queue[: self.batch_size]
        self._queue = self._queue[self.batch_size :]

        if self.scheduler_type == "fifo":
            # FIFO: 保持原始顺序
            pass
        elif self.scheduler_type == "priority":
            # Priority: 按优先级排序
            priority_order = {
                RequestPriority.HIGH: 0,
                RequestPriority.MEDIUM: 1,
                RequestPriority.LOW: 2,
            }
            batch.sort(key=lambda r: priority_order[r.priority])
        elif self.scheduler_type == "slo_aware":
            # SLO-Aware: 按 slack time 排序
            current_time = time.time() * 1000
            for req in batch:
                elapsed = current_time - req.arrival_time_ms
                req._slack = req.slo_target_ms - elapsed
            batch.sort(key=lambda r: r._slack)
        else:  # hybrid
            # Hybrid: 综合优先级和 SLO
            priority_order = {
                RequestPriority.HIGH: 0,
                RequestPriority.MEDIUM: 1,
                RequestPriority.LOW: 2,
            }
            current_time = time.time() * 1000
            for req in batch:
                elapsed = current_time - req.arrival_time_ms
                slack = max(req.slo_target_ms - elapsed, 1)
                priority_score = priority_order[req.priority]
                req._score = 0.6 * priority_score + 0.4 * (1000 / slack)
            batch.sort(key=lambda r: r._score)

        return batch


# ============================================================================
# Map (LLM): LLM 调用
# ============================================================================


class SchedulingLLMMapFunction(MapFunction):
    """Map (LLM): 批量 LLM 调用"""

    def __init__(
        self,
        llm_base_url: str = "http://localhost:8001/v1",
        llm_model: str = "Qwen/Qwen2.5-7B-Instruct",
        timeout: float = 60.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.timeout = timeout

    def execute(
        self, batch: Optional[list[SchedulingRequest]]
    ) -> Optional[list[SchedulingRequest]]:
        """执行 LLM 调用"""
        if batch is None:
            return None

        with httpx.Client(timeout=self.timeout) as client:
            for req in batch:
                response = client.post(
                    f"{self.llm_base_url}/chat/completions",
                    json={
                        "model": self.llm_model,
                        "messages": [{"role": "user", "content": req.query}],
                        "max_tokens": 64,
                        "temperature": 0.7,
                    },
                )
                response.raise_for_status()
                result = response.json()
                req.answer = result["choices"][0]["message"]["content"]
                req.completion_time_ms = time.time() * 1000

        return batch


# ============================================================================
# Sink: 结果输出 + SLO 统计
# ============================================================================


class SchedulingSinkFunction(SinkFunction):
    """Scheduling Sink: 输出结果并统计 SLO"""

    def __init__(self, output_path: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.output_path = output_path
        self.results: list[dict] = []
        self.slo_stats: dict[str, dict] = {
            "high": {"total": 0, "met": 0},
            "medium": {"total": 0, "met": 0},
            "low": {"total": 0, "met": 0},
        }

    def execute(self, batch: Optional[list[SchedulingRequest]]) -> None:
        """输出结果"""
        if batch is None:
            return

        for req in batch:
            priority = req.priority.value
            self.slo_stats[priority]["total"] += 1
            if req.slo_met:
                self.slo_stats[priority]["met"] += 1

            status = "✅" if req.slo_met else "❌"
            print(
                f"{status} [{req.request_id}] {priority} latency={req.latency_ms:.0f}ms (SLO={req.slo_target_ms}ms)"
            )

            result = {
                "request_id": req.request_id,
                "priority": priority,
                "slo_target_ms": req.slo_target_ms,
                "latency_ms": req.latency_ms,
                "slo_met": req.slo_met,
                "answer": req.answer,
            }
            self.results.append(result)

        if self.output_path:
            import json

            with open(self.output_path, "a") as f:
                for r in self.results[-len(batch) :]:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def get_slo_compliance(self) -> dict[str, float]:
        """获取 SLO 合规率"""
        compliance = {}
        for priority, stats in self.slo_stats.items():
            if stats["total"] > 0:
                compliance[priority] = stats["met"] / stats["total"]
            else:
                compliance[priority] = 0.0
        return compliance


# ============================================================================
# Scheduling Pipeline 封装
# ============================================================================


class SchedulingPipeline:
    """Scheduling Pipeline 封装类"""

    def __init__(self, config: SchedulingConfig):
        self.config = config
        self.env: Optional[RemoteEnvironment] = None

    def build(self) -> RemoteEnvironment:
        """构建 Scheduling Pipeline"""
        scheduler = HeadNodeScheduler()

        self.env = RemoteEnvironment(
            "scheduling_pipeline",
            host=self.config.job_manager_host,
            port=self.config.job_manager_port,
            scheduler=scheduler,
        )

        # 构建 Pipeline: Source → Map(Scheduler) → Map(LLM) → Sink
        (
            self.env.from_source(
                SchedulingSourceFunction,
                num_requests=self.config.num_requests,
                high_priority_ratio=self.config.high_priority_ratio,
                medium_priority_ratio=self.config.medium_priority_ratio,
                low_priority_ratio=self.config.low_priority_ratio,
                high_priority_slo_ms=self.config.high_priority_slo_ms,
                medium_priority_slo_ms=self.config.medium_priority_slo_ms,
                low_priority_slo_ms=self.config.low_priority_slo_ms,
            )
            .map(
                SchedulerMapFunction,
                scheduler_type=self.config.scheduler_type.value,
                batch_size=self.config.batch_size,
            )
            .map(
                SchedulingLLMMapFunction,
                llm_base_url=self.config.llm_base_url,
                llm_model=self.config.llm_model,
                timeout=self.config.request_timeout,
            )
            .sink(SchedulingSinkFunction)
        )

        return self.env

    def run(self) -> dict:
        """运行 Pipeline"""
        if self.env is None:
            self.build()

        start_time = time.time()
        try:
            self.env.submit()
            time.sleep(20)  # 调度测试需要更多时间
        finally:
            self.env.close()

        duration = time.time() - start_time
        return {
            "pipeline": "E (Scheduling)",
            "duration_seconds": duration,
            "config": {
                "num_requests": self.config.num_requests,
                "scheduler_type": self.config.scheduler_type.value,
            },
        }
