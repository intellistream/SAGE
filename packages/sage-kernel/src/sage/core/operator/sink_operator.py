from sage.core.operator.base_operator import BaseOperator
from sage.core.api.function.sink_function import SinkFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from collections import deque
from typing import Union, Dict, Deque, Tuple, Any
from sage.core.communication.packet import Packet


class SinkOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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