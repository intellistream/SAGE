from sage_core.operator.base_operator import BaseOperator
from sage_core.api.base_function import BaseFunction
from sage_utils.custom_logger import CustomLogger
from collections import deque
from typing import Union, Dict, Deque, Tuple, Any


class OutputQueueCache:
    def __init__(self, logger: CustomLogger):
        self.queue: Deque[Tuple[int, Any]] = deque()  # 存 (seq, data)
        self.seq: int = 0
        self.acked: int = -1

    def add(self, data):
        self.logger.debug(f"OutputQueueCache:  added data with seq {self.seq}")
        self.queue.append((self.seq, data))
        self.seq += 1

    def ack(self, ack_seq: int):
        """
        Remove items from the front of the queue where seq <= ack_seq
        """
        while self.queue and self.queue[0][0] <= ack_seq:
            self.queue.popleft()
        self.logger.debug(f"OutputQueueCache: acknowledged seq {ack_seq} ")
        self.acked = max(self.acked, ack_seq)
        self.logger.debug(f"OutputQueueCache: current acked seq is {self.acked}")

    def get_unacked(self) -> list[Tuple[int, Any]]:
        return list(self.queue)



class SourceOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output_cache:OutputQueueCache = OutputQueueCache(self.logger)


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

