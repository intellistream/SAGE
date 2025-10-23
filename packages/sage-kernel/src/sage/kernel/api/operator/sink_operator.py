from sage.kernel.api.operator.base_operator import BaseOperator
from sage.kernel.runtime.communication.packet import Packet


class SinkOperator(BaseOperator):
    """
    汇聚操作符 - 数据终点

    流量控制通过Queue的自然机制实现：
    - SinkOperator从queue中取数据并处理
    - 处理完成后queue自动释放空间给上游
    - 无需额外的同步机制
    """

    def process_packet(self, packet: "Packet" = None):
        try:
            if packet is None or packet.payload is None:
                self.logger.warning(f"Operator {self.name} received empty data")
            else:
                result = self.function.execute(packet.payload)
                self.logger.debug(
                    f"Operator {self.name} processed data with result: {result}"
                )
                # Queue机制自动提供背压控制，无需显式同步

        except Exception as e:
            self.logger.error(f"Error in {self.name}.process(): {e}", exc_info=True)

    def handle_stop_signal(self):
        """
        处理停止信号，调用function.close()来触发最终处理
        这个方法会被BaseTask在收到StopSignal时调用
        """
        try:
            self.logger.info(
                f"SinkOperator {self.name} handling stop signal, calling close()"
            )
            if hasattr(self.function, "close") and callable(self.function.close):
                result = self.function.close()
                self.logger.debug(
                    f"SinkOperator {self.name} final processing result: {result}"
                )
            else:
                self.logger.debug(
                    f"SinkOperator {self.name} has no close() method, skipping."
                )
        except Exception as e:
            self.logger.error(
                f"Error in {self.name}.handle_stop_signal(): {e}", exc_info=True
            )
