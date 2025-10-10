from sage.kernel.api.operator.base_operator import BaseOperator
from sage.kernel.runtime.communication.packet import Packet
from sage.kernel.runtime.communication.router.packet import StopSignal


class SourceOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def receive_packet(self, packet: "Packet"):
        self.process_packet(packet)

    def process_packet(self, packet: "Packet" = None):
        try:
            result = self.function.execute()
            self.logger.debug(
                f"Operator {self.name} processed data with result: {result}"
            )

            # 检查是否收到停止信号
            if isinstance(result, StopSignal):
                self.logger.info(
                    f"Source Operator {self.name} received stop signal: {result}"
                )
                result.source = self.name
                self.router.send_stop_signal(result)
                if hasattr(self, "task") and hasattr(self.task, "stop"):
                    self.task.stop()
                    # 对于source operator，收到停止信号后立即标记任务为已停止
                    # 这样dispatcher就能正确检测到任务已停止
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
                    if hasattr(self, "task") and hasattr(self.task, "stop"):
                        self.task.stop()
                    return
        except Exception as e:
            self.logger.error(f"Error in {self.name}.process(): {e}", exc_info=True)
