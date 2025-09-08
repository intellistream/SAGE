from .base_operator import BaseOperator
from typing import Union, Any
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.communication.packet import Packet


class CoMapOperator(BaseOperator):
    """
    CoMap操作符 - 处理多输入流的分别处理操作
    
    CoMapOperator专门用于处理CoMap函数，它会根据输入的input_index
    直接路由到相应的mapN方法，而不是使用统一的execute方法。
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._validated = True
    
    def process_packet(self, packet: 'Packet' = None):
        """CoMap处理多输入，保持分区信息"""
        try:
            if packet is None or packet.payload is None:
                return
            # TODO: 重新设计comap协议，直接用index去call callable的function，让function自己在里边处理
            # 根据输入索引调用对应的mapN方法
            input_index = packet.input_index
            map_method = getattr(self.function, f'map{input_index}')
            result = map_method(packet.payload)
            
            if result is not None:
                # 继承原packet的分区信息
                result_packet = packet.inherit_partition_info(result)
                self.router.send(result_packet)
                
        except Exception as e:
            self.logger.error(f"Error in CoMapOperator {self.name}: {e}", exc_info=True)
            
            # 发送错误结果，确保下游仍能收到数据（关键修复）
            error_result = {
                "type": "comap_error",
                "error": str(e),
                "original_payload": packet.payload if packet else None,
                "input_index": packet.input_index if packet else -1,
                "operator": self.name
            }
            
            try:
                if packet:
                    error_packet = packet.inherit_partition_info(error_result)
                    self.router.send(error_packet)
                    self.logger.info(f"CoMapOperator {self.name}: Sent error result downstream")
            except Exception as send_error:
                self.logger.error(f"Failed to send error result in CoMapOperator {self.name}: {send_error}")
    
    def _get_max_supported_index(self) -> int:
        """
        获取支持的最大输入流索引
        
        Returns:
            int: 最大支持的输入流索引
        """
        max_index = -1
        index = 0
        
        # 检查有多少个mapN方法被实现
        while True:
            method_name = f"map{index}"
            if hasattr(self.function, method_name):
                try:
                    # 尝试调用方法看是否抛出NotImplementedError
                    method = getattr(self.function, method_name)
                    # 检查方法是否为抽象方法或抛出NotImplementedError
                    if not getattr(method, '__isabstractmethod__', False):
                        max_index = index
                except:
                    # 如果获取方法时出错，停止检查
                    break
                index += 1
            else:
                break
        
        return max_index
    
    def get_supported_input_methods(self) -> list[str]:
        """
        获取所有支持的mapN方法列表
        
        Returns:
            list[str]: 支持的方法名列表
        """
        methods = []
        index = 0
        
        while True:
            method_name = f"map{index}"
            if hasattr(self.function, method_name):
                method = getattr(self.function, method_name)
                if not getattr(method, '__isabstractmethod__', False):
                    methods.append(method_name)
                index += 1
            else:
                break
        
        return methods
    
    def __repr__(self) -> str:
        if hasattr(self, 'function') and self.function:
            function_name = self.function.__class__.__name__
            if self._validated:
                max_index = self._get_max_supported_index()
                return f"<{self.__class__.__name__} {function_name} supports:0-{max_index}>"
            else:
                return f"<{self.__class__.__name__} {function_name} (not validated)>"
        else:
            return f"<{self.__class__.__name__} (no function)>"
