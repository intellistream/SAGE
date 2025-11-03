from __future__ import annotations

import logging
from typing import Any

from sage.common.utils.serialization.dill import serialize_object, trim_object_for_ray
from sage.kernel.api.base_environment import BaseEnvironment
from sage.kernel.runtime.jobmanager_client import JobManagerClient

logger = logging.getLogger(__name__)


class RemoteEnvironment(BaseEnvironment):
    """
    简化的远程环境实现
    专注于序列化环境并发送给远程JobManager
    """

    # 序列化时排除的属性
    __state_exclude__ = [
        "logger",
        "_logger",
        "_engine_client",
        "_jobmanager",
        # 移除了'_jobmanager'，因为我们不再使用它
    ]

    def __init__(
        self,
        name: str = "remote_environment",
        config: dict | None = None,
        host: str = "127.0.0.1",
        port: int = 19001,
        scheduler=None,
    ):
        """
        初始化远程环境

        Args:
            name: 环境名称
            config: 环境配置
            host: JobManager服务主机
            port: JobManager服务端口
            scheduler: 调度器，可选。支持字符串 ("fifo", "load_aware") 或 BaseScheduler 实例
        """
        super().__init__(name, config, platform="remote", scheduler=scheduler)

        # 远程连接配置
        self.daemon_host = host
        self.daemon_port = port

        # 客户端连接（延迟初始化）
        self._engine_client: JobManagerClient | None = None

        # 更新配置
        self.config.update({"engine_host": self.daemon_host, "engine_port": self.daemon_port})

        logger.info(f"RemoteEnvironment '{name}' initialized for {host}:{port}")

    @property
    def client(self) -> JobManagerClient:
        """获取JobManager客户端（延迟创建）"""
        if self._engine_client is None:
            logger.debug(f"Creating JobManager client for {self.daemon_host}:{self.daemon_port}")
            self._engine_client = JobManagerClient(host=self.daemon_host, port=self.daemon_port)
        return self._engine_client

    def submit(self, autostop: bool = False) -> str:
        """
        提交环境到远程JobManager

        Args:
            autostop (bool): 如果为True，方法将阻塞直到所有批处理任务完成后自动停止
                           如果为False，方法立即返回，需要手动管理任务生命周期

        Returns:
            环境UUID
        """
        try:
            logger.info(
                f"Submitting environment '{self.name}' to remote JobManager (autostop={autostop})"
            )

            # 第一步：使用 trim_object_for_ray 清理环境，排除不可序列化的内容
            logger.debug("Trimming environment for serialization")
            trimmed_env = trim_object_for_ray(self)

            # 第二步：使用 dill_serializer 打包
            logger.debug("Serializing environment with dill")
            serialized_data = serialize_object(trimmed_env)

            # 第三步：通过JobManager Client发送到JobManager端口
            logger.debug("Submitting serialized environment to JobManager")
            response = self.client.submit_job(serialized_data, autostop=autostop)

            if response.get("status") == "success":
                env_uuid = response.get("job_uuid")
                if env_uuid:
                    self.env_uuid = env_uuid
                    logger.info(f"Environment submitted successfully with UUID: {self.env_uuid}")

                    # 如果启用 autostop，等待作业完成
                    if autostop:
                        self._wait_for_completion()

                    return env_uuid
                else:
                    raise RuntimeError("JobManager returned success but no job UUID")
            else:
                error_msg = response.get("message", "Unknown error")
                raise RuntimeError(f"Failed to submit environment: {error_msg}")

        except Exception as e:
            logger.error(f"Failed to submit environment: {e}")
            raise

    def _wait_for_completion(self):
        """
        等待远程作业完成
        通过轮询JobManager的作业状态来判断是否完成
        """
        import time

        if not self.env_uuid:
            logger.warning("No environment UUID found, cannot wait for completion")
            return

        logger.info("Waiting for remote job to complete...")

        # 设置最大等待时间，避免无限等待
        max_wait_time = 400.0  # 
        start_time = time.time()
        check_interval = 0.5  # 远程检查可以稍微频繁一些

        try:
            while time.time() - start_time < max_wait_time:
                try:
                    # 获取作业状态
                    status_response = self.client.get_job_status(self.env_uuid)

                    # 服务器返回的响应有两层结构:
                    # { "status": "success", "job_status": { "success": True, "status": "running", ... } }
                    # 需要提取内层的 job_status
                    job_status_data = status_response.get("job_status", status_response)

                    # 检查响应是否成功
                    if not job_status_data.get("success", False):
                        error_msg = job_status_data.get("message", "Unknown error")
                        logger.error(f"Error getting job status: {error_msg}")
                        # 如果是 not_found，说明作业已经完成并被清理
                        if job_status_data.get("status") == "not_found":
                            logger.info("Job not found (已完成并清理)")
                            break
                        # 其他错误继续等待
                        time.sleep(check_interval)
                        continue

                    # 获取作业状态
                    job_status = job_status_data.get("status")
                    logger.debug(f"Current job status: {job_status}")

                    if job_status in ["stopped", "failed", "completed"]:
                        logger.info(f"Remote job completed with status: {job_status}")
                        break

                    # 检查 dispatcher 信息
                    dispatcher_info = status_response.get("dispatcher", {})
                    task_count = dispatcher_info.get("task_count", 1)
                    service_count = dispatcher_info.get("service_count", 0)
                    is_running = dispatcher_info.get("is_running", True)

                    logger.debug(
                        f"Dispatcher status: running={is_running}, tasks={task_count}, services={service_count}"
                    )

                    # 如果 dispatcher 已停止且所有资源已清理
                    if not is_running and task_count == 0 and service_count == 0:
                        logger.info("Remote job stopped and all resources cleaned up")
                        break

                except Exception as e:
                    logger.warning(f"Error checking job status: {e}")
                    # 发生错误时也继续等待，可能是网络问题

                time.sleep(check_interval)

            else:
                # 超时了
                logger.warning(f"Timeout waiting for remote job to complete after {max_wait_time}s")
                logger.info("Job may still be running on remote JobManager")

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping remote job...")
            self.stop()
        except Exception as e:
            logger.error(f"Error waiting for completion: {e}")
            try:
                self.stop()
            except Exception as stop_error:
                logger.error(f"Error stopping job after wait error: {stop_error}")

        finally:
            # 确保清理本地资源
            self.is_running = False

    def stop(self) -> dict[str, Any]:
        """
        停止远程环境

        Returns:
            停止操作的结果
        """
        if not self.env_uuid:
            logger.warning("Remote environment not submitted, nothing to stop")
            return {"status": "warning", "message": "Environment not submitted"}

        try:
            logger.info(f"Stopping remote environment {self.env_uuid}")
            response = self.client.pause_job(self.env_uuid)

            if response.get("status") == "success":
                logger.info(f"Environment {self.env_uuid} stopped successfully")
            else:
                logger.warning(f"Stop operation returned: {response}")

            return response

        except Exception as e:
            logger.error(f"Error stopping remote environment: {e}")
            return {"status": "error", "message": str(e)}

    def close(self) -> dict[str, Any]:
        """
        关闭远程环境

        Returns:
            关闭操作的结果
        """
        if not self.env_uuid:
            logger.warning("Remote environment not submitted, nothing to close")
            return {"status": "warning", "message": "Environment not submitted"}

        try:
            logger.info(f"Closing remote environment {self.env_uuid}")
            response = self.client.pause_job(self.env_uuid)

            # 清理本地资源
            self.is_running = False
            self.env_uuid = None
            self.pipeline.clear()

            logger.info("Remote environment closed and local resources cleaned")
            return response

        except Exception as e:
            logger.error(f"Error closing remote environment: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            # 确保本地状态被清理
            self.is_running = False
            self.env_uuid = None

    def health_check(self) -> dict[str, Any]:
        """
        检查远程JobManager健康状态

        Returns:
            健康检查结果
        """
        try:
            logger.debug("Performing health check")
            response = self.client.health_check()
            logger.debug(f"Health check result: {response}")
            return response
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_job_status(self) -> dict[str, Any]:
        """
        获取当前环境作业状态

        Returns:
            作业状态信息
        """
        if not self.env_uuid:
            return {"status": "not_submitted", "message": "Environment not submitted"}

        try:
            logger.debug(f"Getting job status for {self.env_uuid}")
            response = self.client.get_job_status(self.env_uuid)
            return response
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return {"status": "error", "message": str(e)}

    def __repr__(self) -> str:
        return f"RemoteEnvironment(name='{self.name}', host='{self.daemon_host}', port={self.daemon_port})"
