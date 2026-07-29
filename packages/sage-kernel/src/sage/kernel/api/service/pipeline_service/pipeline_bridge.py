"""PipelineBridge - Pipeline-as-Service 核心桥梁

PipelineBridge 是实现 Pipeline-as-Service 的核心组件，
它连接了 Service 调用方和 Pipeline 实现，提供双向通信机制。
"""

from __future__ import annotations

import queue
from dataclasses import dataclass
from typing import Any

from sage.kernel.runtime.communication.packet import StopSignal


@dataclass
class PipelineRequest:
    """Pipeline 请求的数据结构

    Attributes:
        payload: 请求的实际数据（如问题、订单等）
        response_queue: 用于返回结果的队列（每个请求独立）
    """

    payload: dict[str, Any]
    response_queue: queue.Queue[dict[str, Any]]


class PipelineBridge:
    """PipelineBridge - Pipeline-as-Service 的核心桥梁

    【职责】：
    - 接收来自 Service 的请求（submit）
    - 将请求传递给 Pipeline（next）
    - 携带 response_queue 实现结果返回

    【工作流程】：
    ```
    调用方                    PipelineBridge                Pipeline
       │                          │                          │
       ├─ submit(payload) ─────→ │ 创建 response_queue        │
       │                          ├─────────────────────────→ │ Source.next()
       │                          │                          │
       │                          │                          ├─ Map 处理
       │                          │                          │
       │                          │ ←────────────────────────┤ Sink 返回
       ├─ response_queue.get() ←─┤                          │
       │                          │                          │
    ```

    【关闭流程】：
    - close() 发送 StopSignal 到请求队列
    - Pipeline 收到 StopSignal 后自然停止
    - 避免了轮询导致的资源浪费

    【使用场景】：
    - RAG 系统：将检索-生成流程封装为服务
    - 微服务架构：Pipeline 之间相互调用
    - 背压控制：通过阻塞调用实现流量控制
    """

    def __init__(self):
        """初始化 PipelineBridge"""
        self._requests: queue.Queue[PipelineRequest | StopSignal] = queue.Queue()
        self._closed = False

    def submit(self, payload: dict[str, Any]) -> queue.Queue[dict[str, Any]]:
        """提交请求到 Pipeline

        Args:
            payload: 请求数据

        Returns:
            response_queue: 用于获取结果的队列

        Raises:
            RuntimeError: 如果 Bridge 已关闭
        """
        if self._closed:
            raise RuntimeError("Pipeline bridge is closed")

        response_q: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
        req = PipelineRequest(payload=payload, response_queue=response_q)
        self._requests.put(req)
        return response_q

    def next(self, timeout: float = 0.1):
        """获取下一个请求（Pipeline Source 调用）

        Args:
            timeout: 获取请求的超时时间（秒）

        Returns:
            - PipelineRequest: 正常请求
            - StopSignal: 停止信号（bridge 已关闭且队列已空）
            - None: 暂时没有请求（超时）
        """
        if self._closed and self._requests.empty():
            return StopSignal("pipeline-service-shutdown")

        try:
            return self._requests.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self):
        """关闭 Bridge，并主动发送 StopSignal

        这个方法会：
        1. 设置关闭标志
        2. 主动放入 StopSignal 到请求队列
        3. Pipeline Source 收到 StopSignal 后会停止
        """
        if not self._closed:
            self._closed = True
            # 关键：主动放入 StopSignal，让 Pipeline 能够正常停止
            self._requests.put(StopSignal("pipeline-service-shutdown"))

    @property
    def is_closed(self) -> bool:
        """检查 Bridge 是否已关闭"""
        return self._closed
