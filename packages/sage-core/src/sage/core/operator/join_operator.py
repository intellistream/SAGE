from .base_operator import BaseOperator
from typing import Union, Any, List
from sage.core.communication.packet import Packet


class JoinOperator(BaseOperator):
    """
    Join操作符 - 处理多输入流的关联操作
    
    JoinOperator专门用于处理Join函数，它会提取packet的payload、key和tag信息，
    然后调用join function的execute方法进行关联处理。
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 验证函数类型（在运行时初始化后进行）
        self._validate_function()
        self._validated = True
        
        # 统计信息
        self.processed_count = 0
        self.emitted_count = 0

    def _validate_function(self) -> None:
        """
        验证函数是否为Join函数
        
        Raises:
            TypeError: 如果函数不是Join函数
        """
        if not hasattr(self.function, 'is_join') or not self.function.is_join:
            raise TypeError(
                f"{self.__class__.__name__} requires Join function with is_join=True, "
                f"got {type(self.function).__name__}"
            )
        
        # 验证必需的execute方法
        if not hasattr(self.function, 'execute'):
            raise TypeError(
                f"Join function {type(self.function).__name__} must implement execute method"
            )
        
        # 验证execute方法不是抽象方法
        execute_method = getattr(self.function, 'execute')
        if getattr(execute_method, '__isabstractmethod__', False):
            raise TypeError(
                f"Join function {type(self.function).__name__} must implement execute method "
                f"(currently abstract)"
            )
        
        self.logger.debug(f"Validated Join function {type(self.function).__name__}")
    
    def process_packet(self, packet: 'Packet' = None):
        """Join处理，将packet信息传递给join function"""
        try:
            if packet is None or packet.payload is None:
                self.logger.debug("Received empty packet, skipping")
                return
            
            # 必须是keyed packet
            if not packet.is_keyed():
                self.logger.warning(
                    f"JoinOperator '{self.name}' received non-keyed packet, skipping. "
                    f"Join operations require keyed streams."
                )
                return
            
            # 提取必要信息
            payload = packet.payload
            join_key = packet.partition_key
            stream_tag = packet.input_index
            
            self.processed_count += 1
            
            self.logger.debug(
                f"JoinOperator '{self.name}' processing: "
                f"key='{join_key}', tag={stream_tag}, payload_type={type(payload).__name__}"
            )
            
            # 调用join function的execute方法
            join_results = self.function.execute(payload, join_key, stream_tag)
            
            # 处理返回结果
            if join_results is not None:
                # 如果返回的不是列表，转换为列表
                if not isinstance(join_results, list):
                    join_results = [join_results] if join_results is not None else []
                
                # 发送所有结果
                for result in join_results:
                    if result is not None:
                        self._emit_join_result(result, join_key, packet)
                        self.emitted_count += 1
            
            # 定期打印统计信息
            if self.processed_count % 100 == 0:
                self.logger.info(
                    f"JoinOperator '{self.name}' stats: "
                    f"processed={self.processed_count}, emitted={self.emitted_count}, "
                    f"ratio={self.emitted_count / max(1, self.processed_count):.2f}"
                )
                
        except Exception as e:
            self.logger.error(f"Error in JoinOperator '{self.name}': {e}", exc_info=True)
            # 不重新抛出异常，避免中断整个流处理
    
    def _emit_join_result(self, result_data: Any, join_key: Any, original_packet: 'Packet'):
        """
        发送join结果，保持分区信息
        
        Args:
            result_data: join function返回的结果数据
            join_key: 关联键
            original_packet: 原始packet，用于继承其他信息
        """
        try:
            # 创建结果packet，保持分区信息
            result_packet = Packet(
                payload=result_data,
                input_index=0,  # Join的输出默认为0
                partition_key=join_key,
                partition_strategy=original_packet.partition_strategy or "hash",
            )
            
            self.router.send(result_packet)
            
            self.logger.debug(
                f"JoinOperator '{self.name}' emitted result for key '{join_key}': "
                f"{type(result_data).__name__}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to emit join result for key '{join_key}': {e}", exc_info=True)
    
    def get_statistics(self) -> dict:
        """
        获取Join操作统计信息
        
        Returns:
            dict: 统计信息字典
        """
        return {
            "operator_name": self.name,
            "function_type": type(self.function).__name__,
            "processed_packets": self.processed_count,
            "emitted_results": self.emitted_count,
            "join_ratio": self.emitted_count / max(1, self.processed_count),
            "is_validated": self._validated
        }
    
    def debug_print_statistics(self):
        """打印详细的统计信息"""
        stats = self.get_statistics()
        print(f"\n📊 JoinOperator '{self.name}' Statistics:")
        print(f"   Function: {stats['function_type']}")
        print(f"   Processed packets: {stats['processed_packets']}")
        print(f"   Emitted results: {stats['emitted_results']}")
        print(f"   Join ratio: {stats['join_ratio']:.2%}")
        print(f"   Validated: {stats['is_validated']}")
    
    def _validate_execute_method_signature(self) -> bool:
        """
        验证execute方法的签名是否正确
        
        Returns:
            bool: 签名是否正确
        """
        import inspect
        
        try:
            execute_method = getattr(self.function, 'execute')
            signature = inspect.signature(execute_method)
            params = list(signature.parameters.keys())
            
            # 期望的参数：self, payload, key, tag (至少)
            expected_min_params = ['self', 'payload', 'key', 'tag']
            
            if len(params) < len(expected_min_params):
                self.logger.warning(
                    f"Join function execute method has insufficient parameters. "
                    f"Expected: {expected_min_params[1:]}, Got: {params[1:]}"
                )
                return False
            
            # 检查前几个参数名
            for i, expected_param in enumerate(expected_min_params):
                if i < len(params) and params[i] != expected_param:
                    self.logger.warning(
                        f"Join function execute method parameter {i} "
                        f"expected '{expected_param}', got '{params[i]}'"
                    )
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Could not validate execute method signature: {e}")
            return False
    
    def get_supported_stream_count(self) -> int:
        """
        获取支持的输入流数量
        
        目前Join操作支持2个输入流
        
        Returns:
            int: 支持的输入流数量
        """
        return 2  # 目前固定为2流join
    
    def __repr__(self) -> str:
        if hasattr(self, 'function') and self.function:
            function_name = self.function.__class__.__name__
            if self._validated:
                stream_count = self.get_supported_stream_count()
                join_type = getattr(self.function, 'join_type', 'custom')
                return (f"<{self.__class__.__name__} {function_name} "
                       f"type:{join_type} streams:{stream_count} "
                       f"processed:{self.processed_count} emitted:{self.emitted_count}>")
            else:
                return f"<{self.__class__.__name__} {function_name} (not validated)>"
        else:
            return f"<{self.__class__.__name__} (no function)>"