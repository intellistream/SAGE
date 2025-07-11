from sage_core.operator.base_operator import BaseOperator
from sage_core.api.base_function import BaseFunction
from sage_utils.custom_logger import CustomLogger
from collections import deque
from typing import Union, Dict, Deque, Tuple, Any
from sage_runtime.io.packet import Packet

class SourceOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def receive_packet(self, *args, **kwargs):
        self.logger.debug(f"Triggering source operator {self.name}")
        try:
            result = self.function.execute()
            self.logger.debug(f"Source operator {self.name} executed with result: {result}")
            if result is not None:
                self.emit(Packet(result))
        except Exception as e:
            self.logger.error(f"Error in {self.name}.receive_packet(): {e}", exc_info=True)

    # TODO: 在operator中加入响应控制信号的方法
    # def process_control(self, message:Message):
    #     """
    #     Process control messages like WATERMARK, CHECKPOINT, EOS, ACK.
    #     This method can be overridden by subclasses for custom control logic.
        
    #     Args:
    #         message: The control message to process
    #     """
    #     self.logger.debug(f"Processing control message: {message.type}")
    #     if(message.type == "ACK"):
    #         # Handle ACK messages by acknowledging the sequence number
    #         if isinstance(message.payload, int):
    #             self.output_cache.ack(message.payload)
    #             self.logger.debug(f"Acknowledged sequence: {message.payload}")
    #         else:
    #             self.logger.warning("ACK message payload is not an integer sequence number.")

