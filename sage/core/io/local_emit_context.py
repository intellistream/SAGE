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
from sage.core.io.emit_context import BaseEmitContext, DownstreamTarget, NodeType

class LocalEmitContext(BaseEmitContext):
    """
    本地DAG节点使用的Emit Context
    支持向本地节点的输入缓冲区写入数据，向Ray Actor发送远程调用
    """
    
    def __init__(self, node_name: str, session_folder: str = None):
        super().__init__(node_name, session_folder)
    
    def _send_to_local(self, target: DownstreamTarget, data: Any) -> None:
        """
        向本地节点的输入缓冲区写入数据包
        
        Args:
            target: 目标本地节点
            data: 数据
        """
        try:
            # 向下游本地节点的输入缓冲区写入 (输入channel, 数据) 包
            data_packet = (target.target_input_channel, data)
            
            # 假设本地节点有input_buffer属性用于接收数据
            if hasattr(target.target_object, 'input_buffer'):
                target.target_object.input_buffer.put(data_packet)
            elif hasattr(target.target_object, 'put'):
                # 或者有put方法
                target.target_object.put(data_packet)
            else:
                raise AttributeError(f"Local node {target.node_name} has no input_buffer or put method")
                
            self.logger.debug(f"Written data packet to local node {target.node_name}[in:{target.target_input_channel}] input buffer")
            
        except Exception as e:
            self.logger.error(f"Error writing data to local node {target.node_name} input buffer: {e}")
            raise
    
    def _send_to_ray_actor(self, target: DownstreamTarget, data: Any) -> None:
        """
        向Ray Actor发送远程调用
        
        Args:
            target: 目标Ray Actor
            data: 数据
        """
        try:
            if isinstance(target.target_object, ActorHandle):
                # 直接调用Ray Actor的remote方法
                target.target_object.receive.remote(target.target_input_channel, data)
                self.logger.debug(f"Sent remote call to Ray actor {target.node_name}[in:{target.target_input_channel}]")
            else:
                raise TypeError(f"Expected ActorHandle for Ray actor, got {type(target.target_object)}")
                
        except Exception as e:
            self.logger.error(f"Error sending remote call to Ray actor {target.node_name}: {e}")
            raise