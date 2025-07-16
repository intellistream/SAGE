from typing import Any, Iterable, Optional
from sage_core.operator.base_operator import BaseOperator
from sage_core.function.flatmap_function import FlatMapFunction
from sage_core.function.flatmap_collector import Collector
from sage_runtime.io.packet import Packet



class FlatMapOperator(BaseOperator):
    """
    FlatMap操作符，支持将输入数据转换为多个输出数据。
    
    支持两种使用模式：
    1. Function内部调用out.collect()收集数据
    2. Function返回可迭代对象，自动展开发送给下游
    
    Example:
        # 模式1：在function内部使用out.collect()
        def my_function(data):
            words = data.value.split()
            for word in words:
                self.out.collect(word)
        
        # 模式2：function返回可迭代对象
        def my_function(data):
            return data.value.split()
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.out:Collector = Collector(
            operator=self,
            session_folder=self.runtime_context.session_folder,
            name=self.name
        )
        self.function.insert_collector(self.out)
        # # 验证函数类型
        # if not isinstance(self.function, FlatMapFunction):
        #     raise TypeError(f"{self.__class__.__name__} requires FlatMapFunction, got {type(self.function)}")
        





    def process(self, data:Any, input_index: int = 0):
        """
        处理输入数据，支持两种模式：
        1. Function内部调用out.collect()
        2. Function返回可迭代对象
        """
        self.logger.debug(f"FlatMapOperator '{self.name}' processing data : {data}")
        
        try:
            # 清空收集器中的数据（如果有的话）
            self.out.clear()
            
            result = self.function.execute(data)
            
            # 处理function的返回值
            if result is not None:
                self._emit_iterable(result)
            
            # 处理通过collector收集的数据
            if self.out:
                collected_data = self.out.get_collected_data()
                if collected_data:
                    self.logger.debug(f"FlatMapOperator '{self.name}' collected {len(collected_data)} items via out")
                    for item_data in collected_data:
                        self.emit(item_data)
                    # 清空collector
                    self.out.clear()
            
            self.logger.debug(f"FlatMapOperator '{self.name}' finished processing")
            
        except Exception as e:
            self.logger.error(f"Error in FlatMapOperator '{self.name}'.process(): {e}", exc_info=True)

    def _emit_iterable(self, result: Any):
        """
        将可迭代对象展开并发送给下游
        
        Args:
            result: Function的返回值，应该是可迭代对象
            tag: 输出标签
        """
        try:
            # 检查返回值是否为可迭代对象（但不是字符串）
            if hasattr(result, '__iter__') and not isinstance(result, (str, bytes)):
                count = 0
                for item in result:
                    self.emit(item)
                    count += 1
                self.logger.debug(f"FlatMapOperator '{self.name}' emitted {count} items from iterable")
            else:
                # 如果不是可迭代对象，直接发送
                self.emit(result)
                self.logger.debug(f"FlatMapOperator '{self.name}' emitted single item: {result}")
                
        except Exception as e:
            self.logger.error(f"Error in FlatMapOperator '{self.name}'._emit_iterable(): {e}", exc_info=True)
            raise

    def get_collector_statistics(self) -> dict:
        """
        获取collector的统计信息
        
        Returns:
            dict: 统计信息，如果没有collector则返回空字典
        """
        if self.out:
            return self.out.get_statistics()
        return {}

    def debug_print_collector_info(self):
        """
        打印collector的调试信息
        """
        if self.out:
            print(f"\n🔍 FlatMapOperator '{self.name}' Collector Info:")
            self.out.debug_print_collected_data()
        else:
            print(f"\n🔍 FlatMapOperator '{self.name}' has no out")