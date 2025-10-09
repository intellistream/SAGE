from typing import TYPE_CHECKING

import ray
from sage.kernel.runtime.communication.router.packet import Packet
from sage.kernel.runtime.task.base_task import BaseTask

if TYPE_CHECKING:
    from sage.kernel.runtime.factory.operator_factory import OperatorFactory
    from sage.kernel.runtime.context.task_context import TaskContext


@ray.remote
class RayTask(BaseTask):
    """
    基于Ray Actor的任务节点，使用Ray Queue作为输入输出缓冲区
    内部运行独立的工作线程，避免阻塞Ray Actor的事件循环
    """

    def __init__(
        self, runtime_context: "TaskContext", operator_factory: "OperatorFactory"
    ) -> None:

        # 调用父类初始化
        super().__init__(runtime_context, operator_factory)

        self.logger.info(f"Initialized RayTask: {self.ctx.name}")

    def put_packet(self, packet: "Packet"):
        """
        直接向任务的输入缓冲区放入数据包，避免序列化缓冲区对象

        Args:
            packet: 要放入的数据包
        """
        try:
            self.logger.info(
                f"RayTask.put_packet called for {self.ctx.name} with packet: {packet}"
            )
            # 使用异步方式放入数据包以避免死锁
            self.input_buffer.put(packet, block=False)
            self.logger.info(f"RayTask.put_packet succeeded for {self.ctx.name}")
            return True
        except Exception as e:
            self.logger.error(f"RayTask.put_packet failed for {self.ctx.name}: {e}")
            return False
