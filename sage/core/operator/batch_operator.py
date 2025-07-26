from sage.core.operator.base_operator import BaseOperator
from sage.core.function.batch_function import BatchFunction
from sage.utils.custom_logger import CustomLogger
from collections import deque
from typing import Union, Dict, Deque, Tuple, Any, TYPE_CHECKING
from sage.runtime.router.packet import Packet
from sage.core.function.source_function import StopSignal
if TYPE_CHECKING:
    from sage.runtime.task.base_task import BaseTask

class BatchOperator(BaseOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def receive_packet(self, packet: 'Packet'):
        self.process_packet(packet)

    def process_packet(self, packet: 'Packet' = None):
        try:
            result = self.function.execute()
            self.logger.debug(f"Operator {self.name} processed data with result: {result}")
            
            # 如果结果是None，表示批处理完成，发送停止信号
            if result is None:
                self.logger.info(f"Batch Operator {self.name} completed, sending stop signal")
                stop_signal = StopSignal(self.name)
                self.router.send_stop_signal(stop_signal)
                # 通过ctx停止task
                self.ctx.set_stop_signal()
                return
            
            # 如果结果是StopSignal，直接转发
            if isinstance(result, StopSignal):
                self.logger.info(f"Batch Operator {self.name} received stop signal: {result}")
                result.name = self.name
                self.router.send_stop_signal(result)
                self.ctx.set_stop_signal()
                return
            
            # 发送正常数据包
            if result is not None:
                success = self.router.send(Packet(result))
                # If sending failed (e.g., queue is closed), stop the task
                if not success:
                    self.logger.warning(f"Batch Operator {self.name} failed to send packet, stopping task")
                    self.ctx.set_stop_signal()
                    return
                    
        except Exception as e:
            self.logger.error(f"Error in {self.name}.process(): {e}", exc_info=True)
