from __future__ import annotations

from sage_core.environment.batch_environment import BatchEnvironment
from sage_core.environment.stream_environment import StreamEnvironment


class LocalStreamEnvironment(StreamEnvironment):
    """
    本地执行环境（不使用 Ray），用于开发调试或小规模测试。
    """

    def __init__(self, name: str = "local_environment", config: dict | None = None):
        super().__init__(name, config, platform="local")
        self._create_local_jobmanager()

    def submit(self):
        """提交环境到 Engine"""

class LocalBatchEnvironment(BatchEnvironment):
    """
    本地执行环境（不使用 Ray），用于开发调试或小规模测试。
    """

    def __init__(self, name: str = "local_environment", config: dict | None = None):
        super().__init__(name, config, platform="local")
        self._create_local_jobmanager()

    def submit(self):
        """提交Job到 Engine"""
        # Move back the old code Engine-Execute ....