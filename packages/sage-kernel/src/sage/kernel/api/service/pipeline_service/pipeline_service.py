"""PipelineService - Pipeline-as-Service 通用包装器

将 Pipeline 包装为可调用的 Service，实现 Pipeline-as-Service 模式。
"""

from __future__ import annotations

import os
import queue
from typing import Any

from sage.kernel.api.service.base_service import BaseService

from .pipeline_bridge import PipelineBridge

# Test mode detection - reduce timeout in test environments
_IS_TEST_MODE = os.getenv("SAGE_TEST_MODE") == "true" or os.getenv("SAGE_EXAMPLES_MODE") == "test"
_DEFAULT_TIMEOUT = 5.0 if _IS_TEST_MODE else 30.0


class PipelineService(BaseService):
    """Pipeline Service - Pipeline 即服务的通用包装器

    【双重身份】：
    - 对外：是一个 Service，提供 process() 接口
    - 对内：通过 PipelineBridge 连接到真实的 Pipeline

    【工作流程】：
    ```
    1. 主 Pipeline 调用 call_service('service_name', data)
    2. 进入 process() 方法
    3. bridge.submit(data) 提交到服务 Pipeline
    4. **阻塞等待** response_queue.get()
    5. 服务 Pipeline 完成后，结果从 response_queue 返回
    6. 返回给主 Pipeline
    ```

    【背压机制】：
    - process() 方法会阻塞！
    - 主 Pipeline 必须等待服务 Pipeline 完成
    - 这就是背压的实现原理

    【使用示例】：
    ```python
    bridge = PipelineBridge()

    # 注册服务
    env.register_service('my_pipeline', PipelineService, bridge)

    # 创建服务 Pipeline
    env.from_source(PipelineServiceSource, bridge) \\
       .map(YourMapFunction) \\
       .sink(PipelineServiceSink)

    # 在其他 Pipeline 中调用
    # result = self.call_service('my_pipeline', data)
    ```
    """

    def __init__(self, bridge: PipelineBridge, request_timeout: float | None = None):
        """初始化 PipelineService

        Args:
            bridge: PipelineBridge 实例（与服务 Pipeline 共享）
            request_timeout: 请求超时时间（秒），默认 30 秒（测试模式 5 秒）
        """
        super().__init__()
        self._bridge = bridge
        self._request_timeout = request_timeout if request_timeout is not None else _DEFAULT_TIMEOUT

    def process(self, message: dict[str, Any]):
        """处理请求 - 阻塞直到 Pipeline 返回结果

        Args:
            message: 请求数据，可以是任何字典
                   - 特殊命令：{'command': 'shutdown'} 会关闭 Pipeline

        Returns:
            处理结果（从 Pipeline 返回）

        Raises:
            ValueError: 如果消息为空
            RuntimeError: 如果 Bridge 已关闭
            TimeoutError: 如果等待结果超时
        """
        if message is None:
            raise ValueError("Empty message")

        # 处理 shutdown 命令
        if message.get("command") == "shutdown":
            self.logger.info("Shutting down pipeline service")
            self._bridge.close()
            return {"status": "shutdown_ack"}

        # 提交到 Pipeline 并等待结果（阻塞！）
        try:
            response_q = self._bridge.submit(message)
        except RuntimeError as exc:
            raise RuntimeError("Pipeline service is shutting down") from exc

        try:
            result = response_q.get(timeout=self._request_timeout)
            self.logger.debug("Received result from pipeline")
            return result
        except queue.Empty as exc:
            raise TimeoutError(
                f"Pipeline service timed out after {self._request_timeout}s"
            ) from exc

    def stop(self):
        """停止 Pipeline Service

        关闭 PipelineBridge，这会发送 StopSignal 给 Service Pipeline，
        使得 Service Pipeline 中的所有节点能够正常停止。
        """
        self.logger.info(f"Stopping Pipeline Service (bridge: {id(self._bridge)})")
        try:
            self._bridge.close()
            self.logger.info("Pipeline Service stopped successfully")
        except Exception as e:
            self.logger.error(f"Error stopping Pipeline Service: {e}")
