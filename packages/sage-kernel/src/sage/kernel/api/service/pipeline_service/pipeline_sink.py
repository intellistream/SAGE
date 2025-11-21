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
            data: 上游传递的纯数据字典（由 PipelineServiceSource 解包）
                - 包含业务数据字段
                - _response_queue: 用于返回结果的队列（由 Source 附加）
                或者是 StopSignal
        """
        if not data:
            return

        # StopSignal 不需要处理，只是让它通过即可触发停止
        if isinstance(data, StopSignal):
            self.logger.info("Received stop signal, pipeline will stop")
            return

        # 从解包后的数据中提取 response_queue
        if isinstance(data, dict):
            resp_q = data.pop("_response_queue", None)
            # 剩余的就是业务结果
            resp = data
        else:
            # 兼容性：如果不是字典，尝试获取属性
            resp_q = getattr(data, "response_queue", None)
            resp = data

        if resp_q:
            resp_q.put(resp)
            self.logger.debug("Result returned to response queue")
