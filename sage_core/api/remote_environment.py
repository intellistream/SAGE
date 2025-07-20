from __future__ import annotations

from sage_core.environment.batch_environment import BatchEnvironment
from sage_core.environment.stream_environment import StreamEnvironment


class RemoteStreamEnvironment(StreamEnvironment):
    """
    分布式执行环境（Ray），用于生产或大规模部署。
    """

    def __init__(self, name: str = "remote_environment", config: dict | None = None):
        super().__init__(name, config, platform="remote")

    def submit(self, name="example_pipeline"):
        """提交Job到 dispatcher"""
        self._submit_job()


class RemoteBatchEnvironment(BatchEnvironment):
    """
    分布式执行环境（Ray），用于生产或大规模部署。
    """

    def __init__(self, name: str = "remote_environment", config: dict | None = None):
        super().__init__(name, config, platform="remote")

    def submit(self, name="example_pipeline"):
        """提交Job到 dispatcher"""
        self._submit_job()