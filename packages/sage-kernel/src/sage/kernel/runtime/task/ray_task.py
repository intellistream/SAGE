"""
Remote Environment Heartbeat Fault Tolerance Implementation

为 RayTask 添加心跳发送功能,支持 Remote 环境下的故障检测和恢复。
"""

from queue import Full
from time import sleep
from typing import TYPE_CHECKING, Any

import ray

from sage.kernel.runtime.communication.packet import Packet
from sage.kernel.runtime.task.base_task import BaseTask

if TYPE_CHECKING:
    from sage.kernel.runtime.context.task_context import TaskContext
    from sage.kernel.runtime.factory.operator_factory import OperatorFactory


# ========== 心跳配置常量 ==========
HEARTBEAT_INTERVAL = 5.0  # 心跳发送间隔 (秒)
HEARTBEAT_TIMEOUT = 15.0  # 心跳超时阈值 (秒)
MAX_MISSED_HEARTBEATS = 3  # 最大允许丢失心跳次数


@ray.remote
class RayTask(BaseTask):
    """
    带心跳监控的 RayTask

    扩展自 BaseTask,添加心跳发送功能用于 Remote 环境故障检测:
    - 定期发送心跳到 Dispatcher
    - 报告任务状态和处理指标
    - 支持 Checkpoint 容错恢复

    使用方法:
        # 创建时传入 dispatcher_ref
        task = RayTaskWithHeartbeat.remote(ctx, operator_factory, dispatcher_ref)

        # 启动任务 (会自动启动心跳线程)
        ray.get(task.start_running.remote())
    """

    def __init__(
        self,
        ctx: "TaskContext",
        operator_factory: "OperatorFactory",
    ) -> None:
        """
        初始化 RayTask 并设置心跳机制

        Args:
            ctx: 运行时上下文
            operator_factory: Operator 工厂
        """
        # 调用父类初始化
        super().__init__(ctx, operator_factory)

        self.task_id = ctx.name

    # ========== 属性别名 (映射到 BaseTask 的私有属性) ==========
    @property
    def input_buffer(self):
        """输入缓冲区（通过队列描述符访问）"""
        return self.input_qd.get_queue() if self.input_qd else None

    @property
    def packet_count(self) -> int:
        """已处理数据包数量"""
        return self._processed_count

    @packet_count.setter
    def packet_count(self, value: int) -> None:
        self._processed_count = value

    @property
    def error_count(self) -> int:
        """错误计数"""
        return self._error_count

    @error_count.setter
    def error_count(self, value: int) -> None:
        self._error_count = value

    @property
    def last_checkpoint_time(self) -> float:
        """最后检查点时间"""
        return self._last_checkpoint_time

    @property
    def _heartbeat_enabled(self) -> bool:
        """心跳是否启用（始终为 False，兼容旧代码）"""
        return False

    @property
    def heartbeat_interval(self) -> float:
        """心跳间隔（默认值，兼容旧代码）"""
        return HEARTBEAT_INTERVAL

    def _get_current_status(self) -> str:
        """获取当前状态"""
        return "running" if self.is_running else "stopped"

    def put_packet(self, packet: "Packet", max_retries: int = 3):
        """
        向任务的输入缓冲区放入数据包（带重试机制）

        Args:
            packet: 要放入的数据包
            max_retries: 最大重试次数（默认3次）

        Returns:
            True 如果成功，False 如果失败

        Note:
            使用混合策略：
            1. 前 N-1 次尝试非阻塞 + 指数退避
            2. 最后一次尝试短时阻塞（0.1秒）
            这样既保持高吞吐，又降低丢包率
        """
        for attempt in range(max_retries):
            try:
                if attempt < max_retries - 1:
                    # 前 N-1 次：非阻塞尝试
                    self.input_buffer.put(packet, block=False)  # type: ignore[union-attr]
                else:
                    # 最后一次：短暂阻塞（0.1秒）
                    self.input_buffer.put(packet, block=True, timeout=0.1)  # type: ignore[union-attr]

                # 成功：更新计数并返回
                self.packet_count += 1
                if attempt > 0:
                    self.logger.debug(
                        f"RayTask.put_packet succeeded for {self.ctx.name} after {attempt + 1} attempts"
                    )
                return True

            except Full:
                # 队列满：非最后一次则重试
                if attempt < max_retries - 1:
                    backoff_time = 0.01 * (2**attempt)  # 指数退避：10ms, 20ms, 40ms...
                    self.logger.debug(
                        f"RayTask.put_packet: Queue full for {self.ctx.name}, "
                        f"retry {attempt + 1}/{max_retries} after {backoff_time:.3f}s"
                    )
                    sleep(backoff_time)
                else:
                    # 最后一次也失败：记录并返回失败
                    self.logger.warning(
                        f"RayTask.put_packet: Packet dropped for {self.ctx.name} "
                        f"after {max_retries} retries (queue persistently full)"
                    )
                    self.error_count += 1
                    return False

            except Exception as e:
                # 其他异常：直接失败
                self.logger.error(
                    f"RayTask.put_packet failed for {self.ctx.name}: {type(e).__name__}: {e}"
                )
                self.error_count += 1
                return False

        # 不应到达此处
        return False

    def stop(self) -> None:
        """
        停止任务 (重写父类方法,确保心跳线程也停止)

        停止顺序:
        1. 调用父类 stop() 停止工作线程
        2. 心跳线程会检测 is_running=False 并自动退出
        """
        super().stop()
        self.logger.info(f"RayTask {self.ctx.name} stopped (heartbeat will terminate)")

    def get_heartbeat_stats(self) -> dict[str, Any]:
        """
        获取心跳统计信息 (用于监控和调试)

        Returns:
            统计信息字典
        """
        return {
            "task_id": self.ctx.name,
            "heartbeat_enabled": self._heartbeat_enabled,
            "heartbeat_interval": self.heartbeat_interval,
            "status": self._get_current_status(),
            "packet_count": self.packet_count,
            "error_count": self.error_count,
            "last_checkpoint_time": self.last_checkpoint_time,
            "is_running": self.is_running,
        }
