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
    
    使用新的packet-based架构，自动维护分区信息。
    
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
        self.out: Collector = Collector(
            operator=self,
            session_folder=self.runtime_context.session_folder,
            name=self.name
        )
        self.function.insert_collector(self.out)
        self.logger.info(f"FlatMapOperator '{self.name}' initialized with collector")

    def process_packet(self, packet: 'Packet' = None):
        """
        重写packet处理，支持FlatMap的多输出特性
        """
        self.logger.debug(f"FlatMapOperator '{self.name}' received packet, keyed: {packet.is_keyed() if packet else False}")
        
        try:
            if packet is None or packet.payload is None:
                self.logger.debug(f"FlatMapOperator '{self.name}' received empty packet, skipping")
                return
            
            # 清空收集器中的数据（如果有的话）
            self.out.clear()
            
            # 执行flatmap function
            result = self.function.execute(packet.payload)
            
            # 处理function的返回值（如果有）
            if result is not None:
                self._emit_iterable_with_partition_info(result, packet)
            
            # 处理通过collector收集的数据
            collected_data = self.out.get_collected_data()
            if collected_data:
                self.logger.debug(f"FlatMapOperator '{self.name}' collected {len(collected_data)} items via collector")
                for item_data in collected_data:
                    # 为每个收集的item创建新packet，继承分区信息
                    result_packet = packet.inherit_partition_info(item_data)
                    self.router.send(result_packet)
                # 清空collector
                self.out.clear()
            
            # 保存状态逻辑（如果function是StatefulFunction）
            from sage_core.function.base_function import StatefulFunction
            if isinstance(self.function, StatefulFunction):
                self.function.save_state()
            
            self.logger.debug(f"FlatMapOperator '{self.name}' finished processing packet")
            
        except Exception as e:
            self.logger.error(f"Error in FlatMapOperator '{self.name}'.process_packet(): {e}", exc_info=True)

    def _emit_iterable_with_partition_info(self, result: Any, source_packet: 'Packet'):
        """
        将可迭代对象展开并发送给下游，保持分区信息
        
        Args:
            result: Function的返回值，应该是可迭代对象
            source_packet: 源packet，用于继承分区信息
        """
        try:
            # 检查返回值是否为可迭代对象（但不是字符串）
            if hasattr(result, '__iter__') and not isinstance(result, (str, bytes)):
                count = 0
                for item in result:
                    # 为每个item创建新packet，继承分区信息
                    result_packet = source_packet.inherit_partition_info(item)
                    self.router.send(result_packet)
                    count += 1
                self.logger.debug(f"FlatMapOperator '{self.name}' emitted {count} items from iterable")
            else:
                # 如果不是可迭代对象，直接发送
                result_packet = source_packet.inherit_partition_info(result)
                self.router.send(result_packet)
                self.logger.debug(f"FlatMapOperator '{self.name}' emitted single item: {result}")
                
        except Exception as e:
            self.logger.error(f"Error in FlatMapOperator '{self.name}'._emit_iterable_with_partition_info(): {e}", exc_info=True)
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
            print(f"\n🔍 FlatMapOperator '{self.name}' has no collector")

    def emit_data_with_key(self, data: Any, partition_key: Any = None, partition_strategy: str = None):
        """
        便利方法：直接发送带有分区信息的数据
        
        Args:
            data: 要发送的数据
            partition_key: 分区键
            partition_strategy: 分区策略
        """
        packet = Packet(
            payload=data,
            partition_key=partition_key,
            partition_strategy=partition_strategy
        )
        self.router.send(packet)

    def emit_collected_data_with_source_partition(self, source_packet: 'Packet'):
        """
        便利方法：发送collector中的所有数据，继承源packet的分区信息
        
        Args:
            source_packet: 源packet，用于继承分区信息
        """
        collected_data = self.out.get_collected_data()
        if collected_data:
            for item_data in collected_data:
                result_packet = source_packet.inherit_partition_info(item_data)
                self.router.send(result_packet)
            self.out.clear()
            self.logger.debug(f"Emitted {len(collected_data)} collected items with inherited partition info")