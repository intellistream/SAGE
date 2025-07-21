from __future__ import annotations

from sage_core.environment.batch_environment import BatchEnvironment
from sage_core.environment.stream_environment import StreamEnvironment
from sage_utils.actor_wrapper import ActorWrapper


class LocalStreamEnvironment(StreamEnvironment):
    """
    本地执行环境（不使用 Ray），用于开发调试或小规模测试。
    """

    def __init__(self, name: str = "local_environment", config: dict | None = None):
        super().__init__(name, config, platform="local")

    def _get_jobmanager_handle(self) -> ActorWrapper:
        """获取本地JobManager句柄"""
        from sage_jobmanager.job_manager import JobManager
        with JobManager.instance_lock:
            if JobManager.instance is None:
                jobmanager_instance = JobManager(host="127.0.0.1", port=None)
                # 不使用全局的19000端口，使用一个自己的临时端口
            else:
                jobmanager_instance = JobManager.instance
        
        # 用ActorWrapper包装本地JobManager实例
        wrapped_jobmanager = ActorWrapper(jobmanager_instance)
        self.port = jobmanager_instance.tcp_server.port
        self.client.port = self.port
        
        return wrapped_jobmanager

    def submit(self, name="example_pipeline"):
        """提交环境到 Engine"""
        self._submit_to_local_cluster()



class LocalBatchEnvironment(BatchEnvironment):
    """
    本地执行环境（不使用 Ray），用于开发调试或小规模测试。
    """

    def __init__(self, name: str = "local_environment", config: dict | None = None):
        super().__init__(name, config, platform="local")

    def _get_jobmanager_handle(self) -> ActorWrapper:
        """获取本地JobManager句柄"""
        from sage_jobmanager.job_manager import JobManager
        with JobManager.instance_lock:
            if JobManager.instance is None:
                jobmanager_instance = JobManager(host="127.0.0.1", port=None)
                # 不使用全局的19000端口，使用一个自己的临时端口
            else:
                jobmanager_instance = JobManager.instance
        
        # 用ActorWrapper包装本地JobManager实例
        wrapped_jobmanager = ActorWrapper(jobmanager_instance)
        self.port = jobmanager_instance.tcp_server.port
        self.client.port = self.port
        
        return wrapped_jobmanager

    def submit(self, name="example_pipeline"):
        """提交Job到 Engine"""
        self._submit_to_local_cluster()
