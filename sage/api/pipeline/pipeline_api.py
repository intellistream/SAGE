from typing import Type, TYPE_CHECKING, Union, Any
from sage.core.engine import Engine
import pip
from sage.core.engine import Engine
from sage.api.pipeline.datastream_api import DataStream
from sage.api.operator import SourceFunction
from sage.api.operator.base_operator_api import BaseFuction
from sage.api.graph.sage_graph import SageGraph

class Pipeline:
    name:str
    operators: list[BaseFuction]
    data_streams: list[DataStream]
    operator_config: dict
    operator_cls_mapping: dict
    # operator_factory: OperatorFactory
    use_ray: bool
    # compiler: QueryCompiler
    def __init__(self, name: str, use_ray: bool = True):
        self.name = name
        self.operators = []
        self.data_streams = []
        self.operator_config = {}
        self.operator_cls_mapping = {}
        self.use_ray = use_ray
        # 创建全局算子工厂
        # self.operator_factory = OperatorFactory(self.use_ray)


    def _register_operator(self, operator):
        self.operators.append(operator)

    def add_source(self,source_class: Type[SourceFunction], config:dict) -> DataStream:
        """
        添加数据源，自动根据运行时配置创建合适的实例
        
        Args:
            source_class: 算子类（如 FileSource）
            config: 算子配置
        
        Returns:
            DataStream: 数据流对象
        """
        # 使用工厂创建算子实例
        # operator_wrapper = self.operator_factory.create(source_class, config)

        stream = DataStream(source_class,  pipeline=self, name="source", config = config)
        self.data_streams.append(stream)
        return stream

    # def submit(self, config=None,generate_func = None):
    #     # 其中的generate_func最后会传到core.compiler.query_parser中作为generate_func
    #     """
    #     Submit the pipeline to the SAGE engine.
    #     The engine is responsible for compiling and executing the DAG.

    #     Args:
    #         config (dict, optional): Configuration options for runtime execution.
    #             Example:
    #             {
    #                 "is_long_running": True,
    #                 "duration": 1,
    #                 "frequency": 30
    #             }
    #             :param generate_func:
    #     """
    
    #     engine = Engine.get_instance(generate_func)
    #     print(generate_func)
    #     # 建立pipeline与引擎的关联
    #     engine.submit_pipeline(self, config=config or {}) # compile dag -> register engine
    #     print(f"[Pipeline] Pipeline '{self.name}' submitted to engine with config: {config or {}}")




    def stop(self):
        engine= Engine.get_instance() # client side
        engine.stop_pipeline(self) # stop the pipeline
        print(f"[Pipeline] Pipeline '{self.name}' stopped.")

    def add_operator_config(self, config):
        self.operator_config.update(config)

    def add_operator_cls(self, operator_cls):
        self.operator_cls_mapping.update(operator_cls)

    def get_operator_cls(self):
        return self.operator_cls_mapping

    def get_operator_config(self):
        return self.operator_config

    def _merge_configs(self, operator_config):
        """合并全局配置和算子特定配置"""
        merged = {}
        merged.update(self.operator_config)  # 全局算子配置
        merged.update({"runtime": self.runtime_config})  # 运行时配置
        if operator_config:
            merged.update(operator_config)  # 算子特定配置
        return merged
    def set_runtime_config(self, runtime_config: dict):
        """动态设置运行时配置"""
        self.runtime_config = runtime_config
        # self.operator_factory = OperatorFactory(runtime_config)

    def to_graph(self) -> SageGraph:
        """
        将 Pipeline 转换为等价的 SageGraph
        
        Returns:
            SageGraph: 转换后的图结构
        """
        # 创建 SageGraph 实例
        graph_config = {
            "platform": "ray" if self.use_ray else "local",
            "pipeline_name": self.name
        }
        graph = SageGraph(name=f"{self.name}_graph", config=graph_config)
        
        # 构建数据流之间的连接映射
        stream_to_node_name = {}
        stream_connections = {}
        
        # 第一步：为每个 DataStream 生成唯一的节点名和边名
        for i, stream in enumerate(self.data_streams):
            node_name = f"{stream.name}_{i}" if stream.name else f"node_{i}"
            stream_to_node_name[stream] = node_name
            
            # 构建连接映射：记录每个流的上下游边名
            input_edges = []
            output_edges = []
            
            # 处理输入边（来自上游流）
            for j, upstream in enumerate(stream.upstreams):
                edge_name = f"edge_{stream_to_node_name.get(upstream, f'upstream_{j}')}_{node_name}"
                input_edges.append(edge_name)
            
            # 处理输出边（到下游流）
            for j, downstream in enumerate(stream.downstreams):
                downstream_node_name = f"{downstream.name}_{self.data_streams.index(downstream)}" if downstream.name else f"node_{self.data_streams.index(downstream)}"
                edge_name = f"edge_{node_name}_{downstream_node_name}"
                output_edges.append(edge_name)
            
            stream_connections[stream] = {
                'node_name': node_name,
                'input_edges': input_edges,
                'output_edges': output_edges
            }
        
        # 第二步：按拓扑顺序添加节点到图中
        added_nodes = set()
        
        def add_node_recursively(stream: DataStream):
            """递归添加节点，确保上游节点先添加"""
            connection_info = stream_connections[stream]
            node_name = connection_info['node_name']
            
            # 如果节点已添加，跳过
            if node_name in added_nodes:
                return
            
            # 先添加所有上游节点
            for upstream in stream.upstreams:
                add_node_recursively(upstream)
            
            # 添加当前节点
            try:
                graph.add_node(
                    node_name=node_name,
                    input_streams=connection_info['input_edges'],
                    output_streams=connection_info['output_edges'],
                    operator_class=stream.operator,
                    operator_config=stream.config
                )
                added_nodes.add(node_name)
                print(f"Added node: {node_name}")
                
            except Exception as e:
                print(f"Error adding node {node_name}: {e}")
                raise
        
        # 从所有数据流开始添加（以处理可能的多个独立子图）
        for stream in self.data_streams:
            add_node_recursively(stream)
        
        # 第三步：验证图的有效性
        if not graph.validate_graph():
            raise ValueError("Generated graph is invalid")
        
        print(f"Successfully converted pipeline '{self.name}' to graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges")
        return graph

    def submit(self, config=None, generate_func=None):
        """
        Submit the pipeline to the SAGE engine by converting to graph first.
        
        Args:
            config (dict, optional): Configuration options for runtime execution.
            generate_func: Function for query generation
        """
        try:
            # 将 pipeline 转换为 graph
            graph = self.to_graph()
            
            # 合并配置
            if config:
                graph.config.update(config)
            
            # 获取引擎实例并提交图
            engine = Engine.get_instance(generate_func)
            engine.submit_graph(graph)
            
            print(f"[Pipeline] Pipeline '{self.name}' converted to graph and submitted to engine")
            
        except Exception as e:
            print(f"[Pipeline] Failed to submit pipeline '{self.name}': {e}")
            raise

    def get_graph_preview(self) -> dict:
        """
        获取 pipeline 转换为 graph 后的预览信息，不实际提交
        
        Returns:
            dict: 图的结构信息
        """
        try:
            graph = self.to_graph()
            return graph.get_graph_info()
        except Exception as e:
            return {"error": str(e)}