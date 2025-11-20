"""PipelineServiceSource - Pipeline-as-Service 通用 Source

这是服务 Pipeline 的通用 Source 算子，从 PipelineBridge 拉取请求。
"""

from __future__ import annotations

from sage.common.core import SourceFunction
from sage.kernel.runtime.communication.packet import StopSignal

from .pipeline_bridge import PipelineBridge


class PipelineServiceSource(SourceFunction):
    """Pipeline Service 的通用 Source - 从 PipelineBridge 拉取请求

    【职责】：
    - 轮询 PipelineBridge 获取请求
    - 识别并传递 StopSignal 以触发 Pipeline 停止
    - 返回 PipelineRequest 给下游处理

    【关键点】：
    - 这是服务 Pipeline 的入口
    - 通过 bridge.next() 实现阻塞轮询
    - StopSignal 必须透传才能停止 Pipeline

    【使用示例】：
    ```python
    bridge = PipelineBridge()

    env.from_source(PipelineServiceSource, bridge) \\
       .map(YourMapFunction) \\
       .sink(PipelineServiceSink)
    ```
    """

    def __init__(self, bridge: PipelineBridge, poll_interval: float = 0.1):
        """初始化 PipelineServiceSource

        Args:
            bridge: PipelineBridge 实例
            poll_interval: 轮询间隔（秒），默认 0.1 秒
        """
        super().__init__()
        self._bridge = bridge
        self._poll_interval = poll_interval

    def execute(self, data=None):
        """轮询 bridge，获取请求

        Returns:
            - PipelineRequest: 正常请求，继续处理
            - StopSignal: 停止信号，触发 Pipeline 停止
            - None: 暂时没有数据，继续轮询
        """
        req = self._bridge.next(timeout=self._poll_interval)

        if req is None:
            return None

        # 关键：识别并传递 StopSignal
        if isinstance(req, StopSignal):
            self.logger.info(f"Received stop signal: {req}")
            return req

        return req
