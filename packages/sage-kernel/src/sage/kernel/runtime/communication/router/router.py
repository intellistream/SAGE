# sage.kernels.runtime/base_router.py
import traceback

from abc import ABC, abstractmethod
from typing import Dict, Any, TYPE_CHECKING
from sage.kernel.runtime.communication.router.packet import Packet

# 添加 Ray 相关导入以检测 Actor
try:
    import ray
    from ray.actor import ActorHandle
    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False
    ActorHandle = None

if TYPE_CHECKING:
    from sage.kernel.runtime.communication.router.packet import StopSignal
    from sage.kernel.runtime.communication.router.connection import Connection
    from sage.kernel.runtime.context.task_context import TaskContext
    from sage.kernel.runtime.communication.queue_descriptor.base_queue_descriptor import BaseQueueDescriptor

class BaseRouter(ABC):
    """
    路由器基类，负责管理下游连接和数据包路由
    子类只需要实现具体的数据发送逻辑
    """
    
    def __init__(self, ctx: 'TaskContext'):
        self.name = ctx.name
        self.ctx = ctx
        
        # 从TaskContext获取下游连接组信息
        self.downstream_groups: Dict[int, Dict[int, 'Connection']] = ctx.downstream_groups
        self.downstream_group_roundrobin: Dict[int, int] = {}
        
        # 初始化轮询状态
        for broadcast_index in self.downstream_groups.keys():
            self.downstream_group_roundrobin[broadcast_index] = 0
        
        # Logger
        self.logger = ctx.logger
        self.logger.debug(f"Initialized {self.__class__.__name__} for {self.name}")
        self.logger.debug(f"Downstream groups: {list(self.downstream_groups.keys())}")
    
    
    def get_connections_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        info = {}
        for broadcast_index, parallel_targets in self.downstream_groups.items():
            info[f"broadcast_group_{broadcast_index}"] = {
                "count": len(parallel_targets),
                "roundrobin_position": self.downstream_group_roundrobin[broadcast_index],
                "targets": [
                    {
                        "parallel_index": parallel_index,
                        "target_name": connection.target_name,
                        "queue_id": connection.queue_descriptor.queue_id
                    }
                    for parallel_index, connection in parallel_targets.items()
                ]
            }
        return info

    

    def send_stop_signal(self, stop_signal: 'StopSignal') -> None:
        """
        发送停止信号给所有下游连接
        
        Args:
            stop_signal: 停止信号对象
        """
        self.logger.info(f"Sending stop signal: {stop_signal}")
        
        for broadcast_index, parallel_targets in self.downstream_groups.items():
            for connection in parallel_targets.values():
                try:
                    # 通过连接的队列描述符获取队列并发送停止信号
                    queue = connection.queue_descriptor.get_queue()
                    queue.put_nowait(stop_signal)
                    self.logger.debug(f"Sent stop signal to {connection.target_name}")
                except Exception as e:
                    self.logger.error(f"Failed to send stop signal to {connection.target_name}: {e}")

    def send(self, packet: 'Packet') -> bool:
        """
        发送数据包，根据其分区信息选择路由策略
        
        Args:
            packet: 要发送的packet，可能包含分区信息
            
        Returns:
            bool: 是否成功发送
        """
        self.logger.debug(f"Router {self.name}: Send called with downstream_groups: {list(self.downstream_groups.keys())}")
        
        if not self.downstream_groups:
            self.logger.warning(f"No downstream connections available for {self.name}")
            self.logger.warning(f"Current downstream_groups state: {self.downstream_groups}")
            return False
        
        try:
            self.downstream_max_load = 0.0
            self.logger.info(f"Router {self.name}: Sending packet: {packet.payload}")
            self.logger.info(f"Router {self.name}: Downstream groups: {list(self.downstream_groups.keys())}")
            self.logger.debug(f"Emitting packet: {packet}")
            
            # 根据packet的分区信息选择路由策略
            if packet.is_keyed():
                self.logger.info(f"Router {self.name}: Using keyed routing")
                result = self._route_packet(packet)
            else:
                self.logger.info(f"Router {self.name}: Using round-robin routing")
                result = self._route_round_robin_packet(packet)
            
            self.logger.info(f"Router {self.name}: Routing result: {result}")
            self._adjust_delay_based_on_load()
            return True
        except Exception as e:
            self.logger.error(f"Error emitting packet: {e}", exc_info=True)
            return False
    
    def _route_packet(self, packet: 'Packet') -> bool:
        """使用分区信息进行路由"""
        strategy = packet.partition_strategy
        
        if strategy == "hash":
            return self._route_hashed_packet(packet)
        elif strategy == "broadcast":
            return self._route_broadcast_packet(packet)
        else:
            return self._route_round_robin_packet(packet)
    
    def _route_round_robin_packet(self, packet: 'Packet') -> bool:
        """使用轮询策略进行路由"""
        success = True
        
        for broadcast_index, parallel_targets in self.downstream_groups.items():
            if not parallel_targets:  # 空的并行目标组
                continue
                
            # 获取当前轮询位置
            current_round_robin = self.downstream_group_roundrobin[broadcast_index]
            parallel_indices = list(parallel_targets.keys())
            target_parallel_index = parallel_indices[current_round_robin % len(parallel_indices)]
            
            # 更新轮询位置
            self.downstream_group_roundrobin[broadcast_index] = (current_round_robin + 1) % len(parallel_indices)
            
            # 发送到选中的连接
            connection = parallel_targets[target_parallel_index]
            if not self._deliver_packet_to_connection(connection, packet):
                success = False
        
        return success
    
    def _route_broadcast_packet(self, packet: 'Packet') -> bool:
        """使用广播策略进行路由"""
        success = True
        
        for broadcast_index, parallel_targets in self.downstream_groups.items():
            for connection in parallel_targets.values():
                if not self._deliver_packet_to_connection(connection, packet):
                    success = False
        
        return success
    
    def _route_hashed_packet(self, packet: 'Packet') -> bool:
        """使用哈希分区策略进行路由"""
        if not packet.partition_key:
            self.logger.warning("Hash routing requested but no partition key provided, falling back to round-robin")
            return self._route_round_robin_packet(packet)
        
        success = True
        partition_key = packet.partition_key
        
        for broadcast_index, parallel_targets in self.downstream_groups.items():
            if not parallel_targets:
                continue
                
            # 基于分区键计算目标索引
            parallel_indices = list(parallel_targets.keys())
            target_index = hash(partition_key) % len(parallel_indices)
            target_parallel_index = parallel_indices[target_index]
            
            connection = parallel_targets[target_parallel_index]
            if not self._deliver_packet_to_connection(connection, packet):
                success = False
        
        return success
    
    def _deliver_packet_to_connection(self, connection: 'Connection', packet: 'Packet') -> bool:
        """
        将数据包发送到连接对应的队列
        
        Args:
            connection: 目标连接
            packet: 要发送的数据包
            
        Returns:
            bool: 是否成功发送
        """
        try:
            self.logger.info(f"Router {self.name}: Delivering packet to {connection.target_name}")
            
            # 创建路由包，包含target_input_index信息
            routed_packet = self._create_routed_packet(connection, packet)
            
            # 通过连接的队列描述符获取队列
            target_queue = connection.queue_descriptor.get_queue()
            self.logger.info(f"Router {self.name}: Got target queue: {target_queue} (type: {type(target_queue)})")
            
            # 直接发送到队列
            target_queue.put_nowait(routed_packet)
            self.logger.info(f"Router {self.name}: Successfully sent packet to {connection.target_name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Router {self.name}: Failed to deliver packet to {connection.target_name}: {e}")
            traceback.print_exc()
            return False

    
    def clear_all_connections(self):
        """清空所有连接"""
        self.downstream_groups.clear()
        self.downstream_group_roundrobin.clear()
    
    def _create_routed_packet(self, connection: 'Connection', packet: 'Packet') -> 'Packet':
        """创建路由后的数据包"""
        return Packet(
            payload=packet.payload,
            input_index=connection.target_input_index,
            partition_key=packet.partition_key,
            partition_strategy=packet.partition_strategy,
        )
    
    def _adjust_delay_based_on_load(self):
        """根据下游负载调整延迟（目前是占位符实现）"""
        # 这是一个占位符方法，可以在未来根据队列负载情况调整发送延迟
        # 目前不做任何调整
        pass
