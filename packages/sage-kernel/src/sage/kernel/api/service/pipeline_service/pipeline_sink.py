"""PipelineServiceSink - Pipeline-as-Service 通用 Sink

这是服务 Pipeline 的通用 Sink 算子，将结果返回给调用方。
"""

from __future__ import annotations

from sage.common.core import SinkFunction
from sage.kernel.runtime.communication.packet import StopSignal


class PipelineServiceSink(SinkFunction):
    """Pipeline Service 的通用 Sink - 将结果返回给调用方

    【职责】：
    - 将处理结果放入 response_queue
    - PipelineService 会从这个队列获取结果
    - 识别 StopSignal 但不需要特殊处理

    【关键点】：
    - 这是服务 Pipeline 的出口
    - response_queue 实现了结果的异步返回
    - StopSignal 到达后 Pipeline 自然停止

    【使用示例】：
    ```python
    env.from_source(PipelineServiceSource, bridge) \\
       .map(YourMapFunction) \\
       .sink(PipelineServiceSink)
    ```
    """

    def __init__(self):
        """初始化 PipelineServiceSink"""
        super().__init__()

    def execute(self, data):
        """处理数据并返回结果

        Args:
            data: 上游传递的数据，应包含：
                - payload: 处理结果
                - response_queue: 用于返回结果的队列
                或者是 StopSignal
        """
        if not data:
            return

        # StopSignal 不需要处理，只是让它通过即可触发停止
        if isinstance(data, StopSignal):
            self.logger.info("Received stop signal, pipeline will stop")
            return

        # 提取结果和响应队列
        resp = data["payload"] if isinstance(data, dict) and "payload" in data else data
        resp_q = (
            data["response_queue"]
            if isinstance(data, dict) and "response_queue" in data
            else getattr(data, "response_queue", None)
        )

        if resp_q:
            resp_q.put(resp)
            self.logger.debug("Result returned to response queue")
