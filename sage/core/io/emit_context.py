from typing import TypeVar, Generic, Callable, Any, List, Dict, Union, Tuple, Literal
from abc import ABC, abstractmethod
from enum import Enum
import ray
from ray.actor import ActorHandle
import socket
import json
import pickle
import threading
from sage.utils.custom_logger import CustomLogger

class NodeType(Enum):
    LOCAL = "local"
    RAY_ACTOR = "ray_actor"

class DownstreamTarget:
    """下游目标节点的封装"""
    def __init__(self, 
                 node_type: NodeType, 
                 target_object: Any, 
                 target_input_channel: int,
                 node_name: str = None):
        self.node_type = node_type
        self.target_object = target_object
        self.target_input_channel = target_input_channel
        self.node_name = node_name or str(target_object)

class BaseEmitContext(ABC):
    """
    基础Emit Context抽象类
    支持混合环境中本地和Ray Actor之间的通信
    """
    

    def __init__(self, node_name: str):
        self.node_name = node_name
        self.downstream_channels: Dict[int, List[DownstreamTarget]] = {}
        self.downstream_round_robin: dict[int, int] = {}
        # Dict[自身出口号, DownstreamTarget]

    
    def add_downstream_target(self, 
                            output_channel: int,
                            node_type: NodeType, 
                            target_object: Any, 
                            target_input_channel: int,
                            node_name: str = None) -> None:
        """
        添加下游目标节点
        
        Args:
            output_channel: 自身的输出通道号
            node_type: 下游节点类型
            target_object: 下游节点对象
            target_input_channel: 下游节点的输入通道号
            node_name: 下游节点名称
        """
        target = DownstreamTarget(node_type, target_object, target_input_channel, node_name)

        if output_channel not in self.downstream_channels:
            self.downstream_channels[output_channel] = []
            self.downstream_round_robin[output_channel] = 0
        self.downstream_channels[output_channel].append(target)

        
        self.logger.debug(f"Added downstream target: {self.node_name}[out:{output_channel}] -> "
                         f"{node_name}[in:{target_input_channel}] (type: {node_type.value})")
    
    def emit(self, channel: int, data: Any) -> None:
        """
        向指定下游通道发送数据
        
        Args:
            channel: 下游通道索引，-1表示广播到所有通道
            data: 要发送的数据
        """
        if channel == -1:
            # 广播到所有下游通道

            for output_channel, target_lists in self.downstream_channels.items():
                self._send_to_channel(output_channel, data)
        elif channel in self.downstream_channels:
            target = self.downstream_channels[channel]
            self._send_to_channel(channel, data)
        else:
            self.logger.warning(f"Channel index {channel} out of range for node {self.node_name}")
    
    def _send_to_channel(self, channel: int, data: Any) -> None:
        """
        向指定通道发送数据
        
        Args:
            channel: 下游通道索引
            data: 要发送的数据
        """
        if channel in self.downstream_channels:
            targets = self.downstream_channels[channel]
            self._route_and_send(targets[self.downstream_round_robin[channel] % len(targets)], data)
            self.downstream_round_robin[channel] += 1
        else:
            self.logger.warning(f"Channel index {channel} not found in node {self.node_name}")





    def _route_and_send(self, target: DownstreamTarget, data: Any) -> None:
        """
        根据目标类型路由并发送数据
        
        Args:
            target: 目标节点信息
            data: 要发送的数据
        """
        try:
            if target.node_type == NodeType.LOCAL:
                self._send_to_local(target, data)
            elif target.node_type == NodeType.RAY_ACTOR:
                self._send_to_ray_actor(target, data)
            else:
                self.logger.error(f"Unknown target type: {target.node_type}")
        except Exception as e:
            self.logger.error(f"Failed to send data to {target.node_name}: {e}", exc_info=True)
    
    @abstractmethod
    def _send_to_local(self, target: DownstreamTarget, data: Any) -> None:
        """发送数据到本地节点"""
        pass
    
    @abstractmethod
    def _send_to_ray_actor(self, target: DownstreamTarget, data: Any) -> None:
        """发送数据到Ray Actor"""
        pass





