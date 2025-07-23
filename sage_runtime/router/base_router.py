# sage_runtime/base_router.py

from abc import ABC, abstractmethod
from typing import Dict, Any, TYPE_CHECKING
from sage_core.function.source_function import StopSignal
from sage_runtime.router.packet import Packet

if TYPE_CHECKING:
    from sage_runtime.router.connection import Connection
    from sage_runtime.runtime_context import RuntimeContext

class BaseRouter(ABC):
    """
    路由器基类，负责管理下游连接和数据包路由
    子类只需要实现具体的数据发送逻辑
    """
    
    def __init__(self, ctx: 'RuntimeContext'):
        self.name = ctx.name
        self.ctx = ctx
        
        # 下游连接管理
        self.downstream_groups: Dict[int, Dict[int, 'Connection']] = {}
        self.downstream_group_roundrobin: Dict[int, int] = {}
        
        # Logger
        self.logger = ctx.logger
        self.logger.debug(f"Initialized {self.__class__.__name__} for {self.name}")
    
    def add_connection(self, connection: 'Connection') -> None:
        """
        添加下游连接
        
        Args:
            connection: Connection对象，包含所有连接信息
        """
        broadcast_index = connection.broadcast_index
        parallel_index = connection.parallel_index
        
        # Debug log
        self.logger.debug(
            f"Adding connection: broadcast_index={broadcast_index}, parallel_index={parallel_index}, target={connection.target_name}"
        )
        
        # 初始化广播组（如果不存在）
        if broadcast_index not in self.downstream_groups:
            self.downstream_groups[broadcast_index] = {}
            self.downstream_group_roundrobin[broadcast_index] = 0
        
        # 保存完整的Connection对象
        self.downstream_groups[broadcast_index][parallel_index] = connection
        
        self.logger.info(f"Added connection to {connection.target_name}")
    
    def remove_connection(self, broadcast_index: int, parallel_index: int) -> bool:
        """
        移除指定的连接
        
        Args:
            broadcast_index: 广播索引
            parallel_index: 并行索引
            
        Returns:
            bool: 是否成功移除
        """
        try:
            if broadcast_index in self.downstream_groups:
                if parallel_index in self.downstream_groups[broadcast_index]:
                    connection = self.downstream_groups[broadcast_index][parallel_index]
                    del self.downstream_groups[broadcast_index][parallel_index]
                    
                    # 如果这个广播组空了，清理它
                    if not self.downstream_groups[broadcast_index]:
                        del self.downstream_groups[broadcast_index]
                        del self.downstream_group_roundrobin[broadcast_index]
                    else:
                        # 重置轮询计数器
                        self.downstream_group_roundrobin[broadcast_index] = 0
                    
                    self.logger.info(f"Removed connection to {connection.target_name}")
                    return True
            
            self.logger.warning(f"Connection not found: broadcast_index={broadcast_index}, parallel_index={parallel_index}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error removing connection: {e}")
            return False
    
    def get_connection_count(self) -> int:
        """获取总连接数"""
        total = 0
        for parallel_targets in self.downstream_groups.values():
            total += len(parallel_targets)
        return total
    
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
                        "target_name": connection.target_name
                    }
                    for parallel_index, connection in parallel_targets.items()
                ]
            }
        return info
    
    def get_downstream_loads(self) -> Dict[str, float]:
        """
        获取所有下游连接的负载信息
        
        Returns:
            Dict[str, float]: {connection_name: load_ratio}
        """
        loads = {}
        for broadcast_index, parallel_targets in self.downstream_groups.items():
            for parallel_index, connection in parallel_targets.items():
                connection_key = f"{connection.target_name}_{broadcast_index}_{parallel_index}"
                loads[connection_key] = connection.get_buffer_load()
        return loads
    
    def get_max_downstream_load(self) -> float:
        """
        获取下游连接中的最大负载率
        
        Returns:
            float: 最大负载率 (0.0-1.0)
        """
        loads = self.get_downstream_loads()
        return max(loads.values()) if loads else 0.0
    
    def get_downstream_load_stats(self) -> Dict[str, Any]:
        """
        获取下游负载的统计信息
        
        Returns:
            Dict containing load statistics and trends
        """
        loads = []
        increasing_count = 0
        decreasing_count = 0
        
        for broadcast_index, parallel_targets in self.downstream_groups.items():
            for connection in parallel_targets.values():
                load = connection.get_buffer_load()
                loads.append(load)
                
                if connection.is_load_increasing():
                    increasing_count += 1
                elif connection.is_load_decreasing():
                    decreasing_count += 1
        
        if not loads:
            return {
                "max_load": 0.0,
                "avg_load": 0.0,
                "min_load": 0.0,
                "total_connections": 0,
                "increasing_count": 0,
                "decreasing_count": 0,
                "trend": "stable"
            }
        
        max_load = max(loads)
        avg_load = sum(loads) / len(loads)
        min_load = min(loads)
        
        # 判断整体趋势
        if increasing_count > len(loads) * 0.5:
            trend = "increasing"
        elif decreasing_count > len(loads) * 0.5:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "max_load": max_load,
            "avg_load": avg_load,
            "min_load": min_load,
            "total_connections": len(loads),
            "increasing_count": increasing_count,
            "decreasing_count": decreasing_count,
            "trend": trend
        }

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
                    connection.target_buffer.put_nowait(stop_signal)
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
        if not self.downstream_groups:
            self.logger.warning(f"No downstream connections available for {self.name}")
            return False
        
        try:
            self.logger.debug(f"Emitting packet: {packet}")
            
            # 根据packet的分区信息选择路由策略
            if packet.is_keyed():
                return self._route_packet(packet)
            else:
                return self._route_round_robin_packet(packet)
                
        except Exception as e:
            self.logger.error(f"Error emitting packet: {e}")
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
            if not self._deliver_packet(connection, packet):
                success = False
        
        return success
    
    def _route_broadcast_packet(self, packet: 'Packet') -> bool:
        """使用广播策略进行路由"""
        success = True
        
        for broadcast_index, parallel_targets in self.downstream_groups.items():
            for connection in parallel_targets.values():
                if not self._deliver_packet(connection, packet):
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
            if not self._deliver_packet(connection, packet):
                success = False
        
        return success
    
    def _deliver_packet(self, connection: 'Connection', packet: 'Packet') -> bool:
        try:
            # 检查下游负载并动态调整delay
            self._adjust_delay_based_on_load(connection)
            
            routed_packet = self._create_routed_packet(connection, packet)
            target_buffer = connection.target_buffer
            target_buffer.put_nowait(routed_packet)
            self._log_delivery_success(connection, packet)
            return True
        except Exception as e:
            self._log_delivery_failure(connection, e)
            return False
    
    def _adjust_delay_based_on_load(self, connection: 'Connection'):
        """
        根据当前连接的负载动态调整delay
        
        Args:
            connection: 当前发送的目标连接
        """
        try:
            # 获取当前delay
            current_delay = self.ctx.delay
            self.logger.debug(f"Current delay for {connection.target_name}: {current_delay:.3f}s")
            self.logger.debug(f"Connection last load is {connection._last_load :.2f}")
            # 根据当前连接的负载调整delay
            if connection.should_increase_delay():
                # 负载 > 60% 且比上次高，delay增加3%
                new_delay = current_delay * 1.03
                self.ctx.delay = min(new_delay, 2.0)  # 最大不超过2秒
                current_load = connection.get_buffer_load()
                self.logger.debug(f"Load increasing on {connection.target_name} ({current_load:.2f}), increased delay to {self.ctx.delay:.3f}s")
                
            elif connection.should_decrease_delay():
                # 负载 < 30% 且比上次低，delay减少3%
                new_delay = current_delay * 0.97
                self.ctx.delay = max(new_delay, 0.001)  # 最小不低于1ms
                current_load = connection.get_buffer_load()
                self.logger.debug(f"Load decreasing on {connection.target_name} ({current_load:.2f}), decreased delay to {self.ctx.delay:.3f}s")
                
        except Exception as e:
            self.logger.warning(f"Failed to adjust delay based on load: {e}", excinfo=True)

    def clear_all_connections(self):
        """清空所有连接"""
        cleared_count = self.get_connection_count()
        self.downstream_groups.clear()
        self.downstream_group_roundrobin.clear()
        
        self.logger.info(f"Cleared all connections ({cleared_count} connections removed)")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取路由统计信息"""
        return {
            "total_connections": self.get_connection_count(),
            "broadcast_groups": len(self.downstream_groups),
            "connections_by_group": {
                broadcast_index: len(parallel_targets)
                for broadcast_index, parallel_targets in self.downstream_groups.items()
            }
        }
    
    def _create_routed_packet(self, connection: 'Connection', packet: 'Packet') -> 'Packet':
        """创建路由后的数据包"""
        return Packet(
            payload=packet.payload,
            input_index=connection.target_input_index,
            partition_key=packet.partition_key,
            partition_strategy=packet.partition_strategy,
        )
    
    def _log_delivery_success(self, connection: 'Connection', packet: 'Packet'):
        """记录发送成功日志"""
        self.logger.debug(
            f"Sent {'keyed' if packet.is_keyed() else 'unkeyed'} packet "
            f"to {connection.target_name} (strategy: {packet.partition_strategy or 'round-robin'})"
        )
    
    def _log_delivery_failure(self, connection: 'Connection', error: Exception):
        """记录发送失败日志"""
        self.logger.error(f"Failed to send packet to {connection.target_name}: {error}", exc_info=True)