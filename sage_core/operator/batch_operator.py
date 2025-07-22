from sage_core.operator.base_operator import BaseOperator
from sage_core.function.batch_function import BatchFunction
from sage_core.function.source_function import StopSignal
from sage_utils.custom_logger import CustomLogger
from collections import deque
from typing import Union, Dict, Deque, Tuple, Any, TYPE_CHECKING
from sage_runtime.router.packet import Packet

if TYPE_CHECKING:
    from sage_runtime.task.base_task import BaseTask

class BatchOperator(BaseOperator):
    """
    批处理算子
    
    BatchOperator与BatchFunction配合工作，提供更友好的批处理接口。
    它会自动管理批处理的生命周期，在批处理完成后发送停止信号。
    
    主要特性：
    1. 自动跟踪批处理进度
    2. 在完成所有记录后自动发送停止信号
    3. 提供进度监控功能
    4. 支持优雅的错误处理
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._progress_log_interval = kwargs.get('progress_log_interval', 100)  # 每100条记录记录一次进度
        self._last_logged_count = 0

    def receive_packet(self, packet: 'Packet'):
        """
        批处理算子通常作为源算子，不接收上游数据包
        但为了兼容性，仍然实现此方法
        """
        self.logger.warning(f"BatchOperator {self.name} received unexpected packet: {packet}")
        self.process_packet(packet)

    def process_packet(self, packet: 'Packet' = None):
        """
        处理数据包
        
        这是批处理算子的核心逻辑：
        1. 执行批处理函数获取数据
        2. 检查是否完成
        3. 发送数据或停止信号
        """
        try:
            # 确保function是BatchFunction类型
            if not isinstance(self.function, BatchFunction):
                raise ValueError(f"BatchOperator requires BatchFunction, got {type(self.function)}")

            # 执行批处理函数
            result = self.function.execute()
            
            # 记录进度
            self._log_progress_if_needed()
            
            # 检查是否已完成
            if self.function.is_finished():
                self.logger.info(f"Batch Operator {self.name} completed processing")
                
                # 如果还有数据，先发送数据
                if result is not None:
                    self.router.send(Packet(result))
                
                # 发送停止信号
                stop_signal = StopSignal(self.name)
                self.logger.info(f"Batch Operator {self.name} sending stop signal: {stop_signal}")
                self.router.send_stop_signal(stop_signal)
                
                # 停止任务
                if self.task:
                    self.task.stop()
                return
            
            # 如果有数据且未完成，发送数据包
            if result is not None:
                self.router.send(Packet(result))
                self.logger.debug(f"Batch Operator {self.name} sent data: {result}")
            else:
                # 如果没有数据但未标记为完成，可能是数据源问题
                self.logger.warning(f"Batch Operator {self.name} got None result but not finished")
                
        except Exception as e:
            self.logger.error(f"Error in BatchOperator {self.name}.process(): {e}", exc_info=True)
            # 发生错误时也应该发送停止信号
            stop_signal = StopSignal(self.name)
            self.router.send_stop_signal(stop_signal)
            if self.task:
                self.task.stop()

    def _log_progress_if_needed(self):
        """
        根据配置的间隔记录进度日志
        """
        if not isinstance(self.function, BatchFunction):
            return
            
        current_count, total_count = self.function.get_progress()
        
        # 检查是否需要记录进度
        if (current_count - self._last_logged_count >= self._progress_log_interval or 
            self.function.is_finished()):
            
            completion_rate = self.function.get_completion_rate()
            self.logger.info(
                f"Batch Operator {self.name} progress: "
                f"{current_count}/{total_count} ({completion_rate:.1%}) completed"
            )
            self._last_logged_count = current_count

    def get_batch_info(self) -> Dict[str, Any]:
        """
        获取批处理信息
        
        Returns:
            Dict[str, Any]: 包含批处理状态信息的字典
        """
        if not isinstance(self.function, BatchFunction):
            return {"error": "Not a BatchFunction"}
            
        current_count, total_count = self.function.get_progress()
        completion_rate = self.function.get_completion_rate()
        
        return {
            "name": self.name,
            "current_count": current_count,
            "total_count": total_count,
            "completion_rate": completion_rate,
            "is_finished": self.function.is_finished(),
            "progress_percentage": f"{completion_rate:.1%}"
        }

    def reset_batch(self):
        """
        重置批处理状态
        """
        if isinstance(self.function, BatchFunction):
            self.function.reset()
            self._last_logged_count = 0
            self.logger.info(f"Batch Operator {self.name} reset successfully")
        else:
            self.logger.warning(f"Cannot reset non-BatchFunction in {self.name}")

    def force_complete(self):
        """
        强制完成批处理
        """
        self.logger.warning(f"Force completing Batch Operator {self.name}")
        stop_signal = StopSignal(self.name)
        self.router.send_stop_signal(stop_signal)
        if self.task:
            self.task.stop()


class BatchSourceOperator(BatchOperator):
    """
    批处理源算子
    
    BatchSourceOperator是BatchOperator的别名，
    用于更清楚地表示这是一个源算子
    """
    pass
