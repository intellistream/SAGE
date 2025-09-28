from sage.core.communication.packet import Packet
from sage.core.operator.base_operator import BaseOperator


class SinkOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # # 验证函数类型
        # if not isinstance(self.function, SinkFunction):
        #     raise TypeError(f"SinkOperator requires SinkFunction, got {type(self.function)}")

        # 检查function是否启用metronome
        self._metronome = None
        if hasattr(self.function, "use_metronome") and self.function.use_metronome:
            if (
                hasattr(self.function, "metronome")
                and self.function.metronome is not None
            ):
                self._metronome = self.function.metronome
                self.logger.info(
                    f"SinkOperator {self.name} using metronome: {self._metronome.name}"
                )
            else:
                self.logger.warning(
                    f"SinkOperator {self.name} use_metronome=True but no metronome provided"
                )

    def process_packet(self, packet: "Packet" = None):
        try:
            if packet is None or packet.payload is None:
                self.logger.warning(f"Operator {self.name} received empty data")
            else:
                result = self.function.execute(packet.payload)
                self.logger.debug(
                    f"Operator {self.name} processed data with result: {result}"
                )

                # 如果启用了metronome，处理完数据后释放锁
                if self._metronome is not None:
                    self.logger.debug(f"SinkOperator {self.name} releasing metronome")
                    self._metronome.release_once()

        except Exception as e:
            self.logger.error(f"Error in {self.name}.process(): {e}", exc_info=True)

    def handle_stop_signal(self):
        """
        处理停止信号，调用function.execute(None)来触发最终处理
        这个方法会被BaseTask在收到StopSignal时调用
        """
        try:
            self.logger.info(
                f"SinkOperator {self.name} handling stop signal, calling execute(None)"
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
