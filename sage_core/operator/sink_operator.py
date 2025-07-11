from sage_core.operator.base_operator import BaseOperator
from sage_core.function.sink_function import SinkFunction
from sage_utils.custom_logger import CustomLogger
from collections import deque
from typing import Union, Dict, Deque, Tuple, Any
from sage_runtime.io.packet import Packet


class SinkOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # # 验证函数类型
        # if not isinstance(self.function, SinkFunction):
        #     raise TypeError(f"SinkOperator requires SinkFunction, got {type(self.function)}")
        
    def receive_packet(self, packet: 'Packet'):
        self.logger.debug(f"Sink operator {self.name} received packet")
        try:
            result = self.function.execute(packet.payload)
            self.logger.debug(f"Sink operator {self.name} executed with result: {result}")
        except Exception as e:
            self.logger.error(f"Error in {self.name}.receive_packet(): {e}", exc_info=True)