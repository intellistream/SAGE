from collections import deque
from typing import TYPE_CHECKING, Any, Deque, Dict, Tuple, Union

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.function.source_function import SourceFunction
from sage.core.communication.packet import Packet
from sage.core.operator.base_operator import BaseOperator
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
                self.logger.info(f"Source Operator {self.name} received stop signal: {result}")
                result.source = self.name
                self.router.send_stop_signal(result)
                if hasattr(self, 'task') and hasattr(self.task, 'stop'):
                    self.task.stop()
                return
            
            if result is not None:
                self.logger.debug(
                    f"SourceOperator {self.name}: Sending packet with payload: {result}"
                )
                success = self.router.send(Packet(result))
                self.logger.debug(f"SourceOperator {self.name}: Send result: {success}")
                # If sending failed (e.g., queue is closed), stop the task
                if not success:
                    self.logger.warning(f"Source Operator {self.name} failed to send packet, stopping task")
                    if hasattr(self, 'task') and hasattr(self.task, 'stop'):
                        self.task.stop()
                    return
        except Exception as e:
            self.logger.error(f"Error in {self.name}.process(): {e}", exc_info=True)
