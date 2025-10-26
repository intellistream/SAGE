from sage.kernel.api.operator.base_operator import BaseOperator
from sage.kernel.runtime.communication.packet import Packet
from sage.kernel.runtime.communication.router.packet import StopSignal


class SourceOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_signal_sent = False  # 防止重复发送停止信号

    def receive_packet(self, packet: "Packet"):
        self.process_packet(packet)

    def process_packet(self, packet: "Packet | None" = None):
        """
        处理 Source 节点的数据生成

        注意：这里不捕获异常，让异常向上传播到 BaseTask._worker_loop
        在那里统一通过容错机制处理
        """
        # 执行 function.execute()，如果抛出异常则向上传播
        result = self.function.execute()

        self.logger.debug(f"Operator {self.name} processed data with result: {result}")

        # 检查是否收到停止信号
        if isinstance(result, StopSignal):
            # 防止重复处理
            if self._stop_signal_sent:
                return

            self._stop_signal_sent = True

            self.logger.info(
                f"Source Operator {self.name} received stop signal: {result}"
            )

            # 设置停止信号的来源
            result.source = self.name

            # 转发停止信号到下游
            self.router.send_stop_signal(result)

            # 通知 JobManager 该节点停止（与其他节点一致）
            if hasattr(self, "ctx") and hasattr(self.ctx, "request_stop"):
                self.ctx.request_stop()

            # 设置任务停止标志（与其他节点一致）
            if hasattr(self, "task"):
                if hasattr(self.task, "ctx") and hasattr(
                    self.task.ctx, "set_stop_signal"
                ):
                    self.task.ctx.set_stop_signal()

                if hasattr(self.task, "is_running"):
                    self.task.is_running = False

            return

        if result is not None:
            self.logger.debug(
                f"SourceOperator {self.name}: Sending packet with payload: {result}"
            )
            success = self.router.send(Packet(result))
            self.logger.debug(f"SourceOperator {self.name}: Send result: {success}")

            # If sending failed (e.g., queue is closed), stop the task
            if not success:
                self.logger.warning(
                    f"Source Operator {self.name} failed to send packet, stopping task"
                )

                # 生成并发送停止信号
                if not self._stop_signal_sent:
                    self._stop_signal_sent = True
                    stop_signal = StopSignal(f"{self.name}-send-failed")
                    self.router.send_stop_signal(stop_signal)

                    if hasattr(self, "ctx") and hasattr(self.ctx, "request_stop"):
                        self.ctx.request_stop()

                if hasattr(self, "task"):
                    if hasattr(self.task, "ctx"):
                        self.task.ctx.set_stop_signal()
                    if hasattr(self.task, "is_running"):
                        self.task.is_running = False

                return
