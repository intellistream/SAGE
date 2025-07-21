from sage_core.function.source_function import StopSignal
from sage_core.operator.base_operator import BaseOperator
from sage_core.function.sink_function import SinkFunction
from sage_utils.custom_logger import CustomLogger
from collections import deque
from typing import Union, Dict, Deque, Tuple, Any
from sage_runtime.router.packet import Packet


class SinkOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_stop_signals = set()
        self.stop_signal_count = 0
        # # 验证函数类型
        # if not isinstance(self.function, SinkFunction):
        #     raise TypeError(f"SinkOperator requires SinkFunction, got {type(self.function)}")
        
    def process_packet(self, packet: 'Packet' = None):
        try:
            if packet is None or packet.payload is None:
                self.logger.warning(f"Operator {self.name} received empty data")
            else:
                result = self.function.execute(packet.payload)
                self.logger.debug(f"Operator {self.name} processed data with result: {result}")
        except Exception as e:
            self.logger.error(f"Error in {self.name}.process(): {e}", exc_info=True)

    def handle_stop_signal(self, stop_signal: StopSignal):
        """
        处理停止信号
        """
        if stop_signal.name in self.received_stop_signals:
            self.logger.debug(f"Already received stop signal from {stop_signal.name}")
            return
        
        self.received_stop_signals.add(stop_signal.name)
        self.logger.info(f"Handling stop signal from {stop_signal.name}")

        self.stop_signal_count += 1
        if self.stop_signal_count >= self.ctx.stop_signal_num:
            self.ctx.jobmanager.receive_stop_signal(self.ctx.env_uuid)