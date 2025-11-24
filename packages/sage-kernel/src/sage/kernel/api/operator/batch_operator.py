from sage.kernel.api.operator.base_operator import BaseOperator
from sage.kernel.runtime.communication.packet import Packet, StopSignal


class BatchOperator(BaseOperator):
    """
    批处理操作符

    流量控制通过router的Queue实现：
    - router.send(packet)内部使用queue.put()
    - 当下游处理慢时，put()会自然阻塞，形成背压
    - 无需额外的全局锁机制
    """

    def receive_packet(self, packet: "Packet"):
        self.process_packet(packet)

    def process_packet(self, packet: "Packet | None" = None):
        try:
            result = self.function.execute()
            self.logger.debug(f"Operator {self.name} processed data with result: {result}")

            # 检查是否为停止信号
            is_stop = result is None or isinstance(result, StopSignal)

            if is_stop:
                self.logger.info(f"Batch Operator {self.name} completed, sending stop signal")

                # 使用标准 StopSignal
                if isinstance(result, StopSignal):
                    stop_signal = result
                else:
                    stop_signal = StopSignal(self.name)

                self.router.send_stop_signal(stop_signal)

                # 源节点完成时,通知JobManager该节点完成
                self.ctx.send_stop_signal_back(self.name)

                # 通过ctx停止task
                self.ctx.set_stop_signal()
                return

            # 发送正常数据包
            # router.send()内部的queue.put()会在队列满时自动阻塞，实现背压控制
            if result is not None:
                success = self.router.send(Packet(result))
                # If sending failed (e.g., queue is closed), stop the task
                if not success:
                    self.logger.warning(
                        f"Batch Operator {self.name} failed to send packet, stopping task"
                    )
                    self.ctx.set_stop_signal()
                    return

        except Exception as e:
            self.logger.error(f"Error in {self.name}.process(): {e}", exc_info=True)
