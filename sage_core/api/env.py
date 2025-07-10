from __future__ import annotations

import time
from typing import Type, Union, Any, List
from enum import Enum
import sage_memory.api
from sage_core.api.base_function import BaseFunction
from sage_core.api.datastream import DataStream
from sage_core.api.transformation import TransformationType, Transformation
from sage_utils.custom_logger import CustomLogger
from sage_core.api.enum import PlatformType
from sage_utils.name_server import get_name
class BaseEnvironment:

    def __init__(self, name: str, config: dict | None, *, platform: PlatformType = PlatformType.LOCAL):
        self.name = get_name(name)
        self.logger = CustomLogger(
            filename=f"Environment_{name}",
            env_name = name,
            console_output="WARNING",
            file_output=True,
            global_output = "DEBUG",
        )
        

        self.config: dict = dict(config or {})
        self.platform:PlatformType = platform
        # 用于收集所有 Transformation，供 Compiler 构建 DAG
        self._pipeline: List[Transformation] = []
        self.runtime_context = dict  # 需要在compiler里面实例化。
        self.memory_collection = None  # 用于存储内存集合
        self.is_running = False

    def from_source(
        self, 
        function: Union[BaseFunction, Type[BaseFunction]], 
        *args, 
        platform:PlatformType = PlatformType.LOCAL,
        **kwargs: Any) -> DataStream:
        
        """用户 API：声明一个数据源并返回 DataStream 起点。"""
        transformation = Transformation(
            self, 
            TransformationType.SOURCE, 
            function, 
            *args,
            platform = platform,  
            **kwargs
            )
        
        self._pipeline.append(transformation)
        return DataStream(self, transformation)

    # TODO: add a new type of source with handler returned.
    def create_source(self):
        pass

    def submit(self, name="example_pipeline"):
        self.debug_print_pipeline()
        from sage_core.core.engine import Engine
        engine = Engine.get_instance()
        engine.submit_env(self)
        # time.sleep(10) # 等待管道启动
        while (self.initialized() is False):
            time.sleep(1)

    def run_once(self, node:str = None):
        """
        运行一次管道，适用于测试或调试。
        """
        if(self.is_running):
            self.logger.warning("Pipeline is already running. ")
            return
        from sage_core.core.engine import Engine
        engine = Engine.get_instance()
        engine.run_once(self)
        # time.sleep(10) # 等待管道启动

    def run_streaming(self, node: str = None):
        """
        运行管道，适用于生产环境。
        """
        from sage_core.core.engine import Engine
        engine = Engine.get_instance()
        engine.run_streaming(self)
        # time.sleep(10) # 等待管道启动

    def stop(self):
        """
        停止管道运行。
        """
        self.logger.info("Stopping pipeline...")
        from sage_core.core.engine import Engine
        engine = Engine.get_instance()
        engine.stop_pipeline(self)
        self.close()

    def close(self):
        """
        关闭管道运行。
        """
        from sage_core.core.engine import Engine
        engine = Engine.get_instance()
        # 1) 停止本环境对应的 DAG 执行
        engine.stop_pipeline(self)
        # 2) 关闭该环境在 Engine 中的引用，并在无剩余环境时彻底 shutdown Engine
        engine.close_pipeline(self)
        # 3) 清理自身引用，以打破循环链
        self._pipeline.clear()

    @property
    def pipeline(self) -> List[Transformation]:  # noqa: D401
        """返回 Transformation 列表（Compiler 会使用）。"""
        return self._pipeline

    def set_memory(self, config):
        self.memory_collection = sage_memory.api.get_memory(self, config, remote = (self.platform == PlatformType.REMOTE))

    def set_memory_collection(self, collection):

        self.memory_collection = collection 
        
    # TODO: 写一个判断Env 是否已经完全初始化并开始执行的函数
    def initialized(self):
        pass

    def debug_print_pipeline(self):
        """
        调试方法：打印环境及其包含的所有Transformation的详细信息
        """
        lines = []
        lines.append("\n")
        lines.append("=" * 80)
        lines.append(f"Environment Debug Information: '{self.name}'")
        lines.append("=" * 80)
        
        # 显示环境基本信息
        lines.append(f"\n🏗️  Environment Details:")
        lines.append(f"   Name: {self.name}")
        lines.append(f"   Platform: {self.platform.value}")
        lines.append(f"   Running: {self.is_running}")
        lines.append(f"   Pipeline Size: {len(self._pipeline)} transformations")
        
        # 显示配置信息
        if self.config:
            lines.append(f"   Configuration:")
            for key, value in self.config.items():
                lines.append(f"     {key}: {value}")
        else:
            lines.append(f"   Configuration: None")
            
        # 显示内存配置
        if self.memory_collection:
            lines.append(f"   Memory Collection: Configured")
        else:
            lines.append(f"   Memory Collection: None")
        
        if not self._pipeline:
            lines.append("\n📝 Pipeline: Empty")
            self.logger.debug("\n".join(lines))
            return
        
        # 按类型分组显示 Transformations
        transformation_groups = {}
        for i, transformation in enumerate(self._pipeline):
            trans_type = transformation.type.value
            if trans_type not in transformation_groups:
                transformation_groups[trans_type] = []
            transformation_groups[trans_type].append((i, transformation))
        
        lines.append(f"\n📝 Pipeline Transformations:")
        lines.append(f"   Transformation Types: {len(transformation_groups)}")
        
        for trans_type, trans_list in transformation_groups.items():
            lines.append(f"\n   📊 Type: {trans_type.upper()}")
            lines.append(f"      Count: {len(trans_list)}")
            
            for pipeline_index, transformation in trans_list:
                lines.append(f"\n      🔗 [{pipeline_index}] Name: {transformation.basename}")
                lines.append(f"         Function: {transformation.function_class.__name__}")
                lines.append(f"         Parallelism: {transformation.parallelism}")
                lines.append(f"         Platform: {transformation.platform.value if hasattr(transformation, 'platform') else 'N/A'}")
                
                # 显示是否已实例化
                if transformation.is_instance:
                    lines.append(f"         Instance: ✓ (pre-instantiated)")
                else:
                    lines.append(f"         Instance: ✗ (will instantiate at runtime)")
                
                # 显示函数参数
                if transformation.function_args:
                    lines.append(f"         Args: {transformation.function_args}")
                if transformation.kwargs:
                    lines.append(f"         Kwargs: {transformation.kwargs}")
                    
                # 显示输入连接
                if transformation.upstreams:
                    lines.append(f"         📥 Inputs ({len(transformation.upstreams)}):")
                    for input_tag, (upstream_trans, upstream_tag) in transformation.upstreams.items():
                        upstream_name = upstream_trans.basename
                        lines.append(f"           '{input_tag}' ← {upstream_name}['{upstream_tag}']")
                else:
                    lines.append(f"         📥 Inputs: None (source transformation)")
                
                # 显示输出连接
                if transformation.downstreams:
                    total_downstream_connections = sum(len(downstream_set) for downstream_set in transformation.downstreams.values())
                    lines.append(f"         📤 Outputs ({total_downstream_connections} connections):")
                    for output_tag, downstream_set in transformation.downstreams.items():
                        if downstream_set:
                            downstream_names = [f"{down_trans.basename}['{down_tag}']" 
                                             for down_trans, down_tag in downstream_set]
                            lines.append(f"           '{output_tag}' → {downstream_names}")
                        else:
                            lines.append(f"           '{output_tag}' → None")
                else:
                    lines.append(f"         📤 Outputs: None (sink transformation)")
                
                # 显示声明的输入输出标签
                declared_inputs = transformation.function_class.declare_inputs()
                declared_outputs = transformation.function_class.declare_outputs()
                lines.append(f"         🏷️  Declared Tags:")
                lines.append(f"           Inputs: {[tag for tag, _ in declared_inputs]}")
                lines.append(f"           Outputs: {[tag for tag, _ in declared_outputs]}")
        
        # 显示拓扑连接信息
        lines.append(f"\n🔄 Pipeline Topology:")
        for i, transformation in enumerate(self._pipeline):
            downstream_names = []
            for output_tag, downstream_set in transformation.downstreams.items():
                for down_trans, down_tag in downstream_set:
                    downstream_names.append(f"{down_trans.basename}[{down_tag}]")
            
            if downstream_names:
                lines.append(f"   [{i}] {transformation.basename} → {downstream_names}")
            else:
                lines.append(f"   [{i}] {transformation.basename} → [SINK]")
        
        # 显示数据流验证信息
        lines.append(f"\n✅ Pipeline Validation:")
        source_count = sum(1 for trans in self._pipeline if trans.type == TransformationType.SOURCE)
        sink_count = sum(1 for trans in self._pipeline if trans.type == TransformationType.SINK)
        
        lines.append(f"   Sources: {source_count}")
        lines.append(f"   Sinks: {sink_count}")
        
        # 检查连接完整性
        unconnected_inputs = []
        unconnected_outputs = []
        
        for transformation in self._pipeline:
            # 检查未连接的输入
            declared_inputs = transformation.function_class.declare_inputs()
            for input_tag, _ in declared_inputs:
                if input_tag not in transformation.upstreams:
                    unconnected_inputs.append(f"{transformation.basename}[{input_tag}]")
            
            # 检查未连接的输出（除了sink类型）
            if transformation.type != TransformationType.SINK:
                declared_outputs = transformation.function_class.declare_outputs()
                for output_tag, _ in declared_outputs:
                    if output_tag not in transformation.downstreams or not transformation.downstreams[output_tag]:
                        unconnected_outputs.append(f"{transformation.basename}[{output_tag}]")
        
        if unconnected_inputs:
            lines.append(f"   ⚠️  Unconnected Inputs: {unconnected_inputs}")
        else:
            lines.append(f"   ✓ All inputs connected")
            
        if unconnected_outputs:
            lines.append(f"   ⚠️  Unconnected Outputs: {unconnected_outputs}")
        else:
            lines.append(f"   ✓ All outputs connected or are sinks")
        
        lines.append("=" * 80)
        
        # 一次性输出所有调试信息
        self.logger.debug("\n".join(lines))

class LocalEnvironment(BaseEnvironment):
    """
    本地执行环境（不使用 Ray），用于开发调试或小规模测试。
    """

    def __init__(self, name: str = "local_environment", config: dict | None = None):
        super().__init__(name, config, platform=PlatformType.LOCAL)


class RemoteEnvironment(BaseEnvironment):
    """
    分布式执行环境（Ray），用于生产或大规模部署。
    """

    def __init__(self, name: str = "remote_environment", config: dict | None = None):
        super().__init__(name, config, platform=PlatformType.REMOTE)


class DevEnvironment(BaseEnvironment):
    """
    混合执行环境，可根据配置动态选择本地或 Ray。
    config 中可包含 'use_ray': bool 来切换运行时。
    """

    def __init__(self, name: str = "dev_environment", config: dict | None = None):
        cfg = dict(config or {})
        super().__init__(name, cfg, platform=PlatformType.HYBRID)
