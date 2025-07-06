from typing import Any
from ray.actor import ActorHandle
from sage_runtime.io.emit_context import BaseEmitContext, DownstreamTarget


class LocalEmitContext(BaseEmitContext):
    """
    本地DAG节点使用的Emit Context
    支持向本地节点的输入缓冲区写入数据，向Ray Actor发送远程调用
    """
    

    def __init__(self):
        pass
    def _send_to_local(self, target: DownstreamTarget, data: Any) -> None:
        """
        向本地节点的输入缓冲区写入数据包
        
        Args:
            target: 目标本地节点
            data: 数据
        """
        try:
            # 向下游本地节点的输入缓冲区写入 (输入channel, 数据) 包
            data_packet = (target.input_tag, data)
            
            # 假设本地节点有input_buffer属性用于接收数据
            if hasattr(target.target_object, 'input_buffer'):
                target.target_object.input_buffer.put(data_packet)
            elif hasattr(target.target_object, 'put'):
                # 或者有put方法
                target.target_object.put(data_packet)
            else:
                raise AttributeError(f"Local node {target.target_object} has no input_buffer or put method")
                
            self.logger.debug(f"Written data packet to local node {target.target_object}[in:{target.input_tag}] input buffer")
            
        except Exception as e:
            self.logger.error(f"Error writing data to local node {target.target_object} input buffer: {e}")
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
                target.target_object.receive.remote(target.input_tag, data)
                self.logger.debug(f"Sent remote call to Ray actor {target.target_object}[in:{target.input_tag}]")
            else:
                raise TypeError(f"Expected ActorHandle for Ray actor, got {type(target.target_object)}")
                
        except Exception as e:
            self.logger.error(f"Error sending remote call to Ray actor {target.target_object}: {e}")
            raise