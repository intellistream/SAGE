from typing import Union, Any
from dataclasses import dataclass
import time

# Import Ray components safely
try:
    from ray.actor import ActorHandle
    RAY_AVAILABLE = True
except ImportError:
    ActorHandle = None
    RAY_AVAILABLE = False

from sage.runtime.task.base_task import BaseTask
from sage.utils.actor_wrapper import ActorWrapper

@dataclass
class Connection:
    """
    用于表示本地节点和Ray Actor之间的连接
    """
    def __init__(self,
                 broadcast_index: int,
                 parallel_index: int,
                 target_name: str,
                 target_handle: Any,  # Union[ActorHandle, BaseTask, ActorWrapper] - using Any to avoid import issues
                 target_input_index: int,
                 target_type: str = "local"):
        
        # 目前我们使用ray也只是在一台机器上
        self.broadcast_index: int = broadcast_index
        self.parallel_index: int = parallel_index
        self.target_name: str = target_name
        
        # 如果target_handle是Ray Actor，用ActorWrapper包装
        is_ray_actor = False
        if RAY_AVAILABLE and ActorHandle and isinstance(target_handle, ActorHandle):
            is_ray_actor = True
        elif hasattr(target_handle, '__class__') and 'ActorHandle' in str(type(target_handle)):
            # 额外的安全检查，防止import问题
            is_ray_actor = True
        
        if is_ray_actor:
            self.target_handle = ActorWrapper(target_handle)
            # 如果传入的是裸露的Ray Actor，应该设置为ray类型
            if target_type == "local":
                target_type = "ray"
        else:
            self.target_handle = target_handle
            
        self.target_input_index: int = target_input_index
        self.target_type: str = target_type
        # 负载状态跟踪
        self._load_history = []  # 存储最近的负载历史
        self._last_load_check = time.time()
        self._load_trend = 0.0  # 负载趋势：正数表示增加，负数表示减少
        self._max_history_size = 10  # 保存最近10次的负载记录
    
    def get_buffer_load(self) -> float:
        """
        获取目标缓冲区的负载率 (0.0-1.0)
        """
        try:
            # 检查是否为Python标准队列
            if hasattr(self.target_buffer, 'qsize') and hasattr(self.target_buffer, 'maxsize'):
                current_size = self.target_buffer.qsize()
                max_size = self.target_buffer.maxsize
                if max_size > 0:
                    load_ratio = current_size / max_size
                else:
                    load_ratio = 0.0
            # 检查是否为Ray队列
            elif hasattr(self.target_buffer, 'size') and hasattr(self.target_buffer, 'maxsize'):
                current_size = self.target_buffer.size()
                max_size = self.target_buffer.maxsize
                if max_size > 0:
                    load_ratio = current_size / max_size
                else:
                    load_ratio = 0.0
            else:
                # 其他类型（ObjectRef等），暂时返回0
                # 在实际使用中，Ray Queue通过ActorWrapper应该可以直接访问size()方法
                load_ratio = 0.0
            
            return load_ratio
            
        except Exception as e:
            # 如果获取负载失败，记录调试信息并返回0
            # 这可能发生在Ray远程调用失败时
            return 0.0
    
    # def should_increase_delay(self) -> bool:
    #     """
    #     判断是否应该增加delay
    #     当前负载 > 60% 且比上次记录的高
    #     """
    #     current_load = self.get_buffer_load()
    #     return current_load > 0.6
    
    # def should_decrease_delay(self) -> bool:
    #     """
    #     判断是否应该减少delay
    #     当前负载 < 30% 且比上次记录的低
    #     """
    #     current_load = self.get_buffer_load()
    #     return current_load < 0.3
    
    # def _update_load_history(self, current_load: float):
    #     """更新负载历史和计算趋势"""
    #     current_time = time.time()
        
    #     # 添加到历史记录
    #     self._load_history.append((current_time, current_load))
        
    #     # 保持历史记录大小
    #     if len(self._load_history) > self._max_history_size:
    #         self._load_history.pop(0)
        
    #     # 计算负载趋势（最近3个点的斜率）
    #     if len(self._load_history) >= 3:
    #         recent_points = self._load_history[-3:]
    #         # 计算简单的线性趋势
    #         time_diff = recent_points[-1][0] - recent_points[0][0]
    #         load_diff = recent_points[-1][1] - recent_points[0][1]
            
    #         if time_diff > 0:
    #             self._load_trend = load_diff / time_diff
    #         else:
    #             self._load_trend = 0.0
        
    #     self._last_load_check = current_time
    
    def get_load_trend(self) -> float:
        """
        获取负载趋势
        返回值：正数表示负载增加，负数表示负载减少，0表示稳定
        """
        return self._load_trend
    
    def is_load_increasing(self) -> bool:
        """负载是否在增加"""
        return self._load_trend > 0.05  # 5%/秒的增长视为增加
    
    def is_load_decreasing(self) -> bool:
        """负载是否在减少"""
        return self._load_trend < -0.05  # 5%/秒的减少视为减少