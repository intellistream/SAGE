"""
Remote Environment Heartbeat Fault Tolerance Implementation

为 RayTask 添加心跳发送功能,支持 Remote 环境下的故障检测和恢复。
"""

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

    def put_packet(self, packet: "Packet"):
        """
        向任务的输入缓冲区放入数据包

        Args:
            packet: 要放入的数据包

        Returns:
            True 如果成功
        """
        try:
            self.logger.debug(
                f"RayTask.put_packet called for {self.ctx.name} with packet: {packet}"
            )
            # 使用非阻塞方式放入数据包 (input_buffer 在运行时总是有值)
            self.input_buffer.put(packet, block=False)  # type: ignore[union-attr]
            self.packet_count += 1  # 更新计数
            self.logger.debug(f"RayTask.put_packet succeeded for {self.ctx.name}")
            return True
        except Exception as e:
            self.logger.error(f"RayTask.put_packet failed for {self.ctx.name}: {e}")
            self.error_count += 1  # 更新错误计数
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
