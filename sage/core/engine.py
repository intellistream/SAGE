from typing import Type, TYPE_CHECKING, Union, Any, TYPE_CHECKING
from sage.core.compiler.query_compiler import QueryCompiler
from sage.core.runtime.runtime_manager import RuntimeManager
from sage.utils.custom_logger import CustomLogger
from sage.core.dag.mixed_dag import MixedDAG
import threading, typing, logging

class Engine:
    _instance = None
    _lock = threading.Lock()
    def __init__(self):

        # 确保只初始化一次
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        # self.dag_manager = DAGManager() # deprecated
        self.runtime_manager = RuntimeManager.get_instance()
        self.compiler= QueryCompiler()
        from sage.core.graph import SageGraph
        self.graphs:dict[str, SageGraph] = {}  # 存储 pipeline 名称到 SageGraph 的映射
        self.dags:dict = {} # 存储name到dag的映射，其中dag的类型为DAG或RayDAG

        self.logger = CustomLogger(
            object_name=f"SageEngine",
            log_level="DEBUG",
            console_output=False,
            file_output=True
        )


    def __new__(cls):
        # 禁止直接实例化
        raise RuntimeError("请通过 get_instance() 方法获取实例")

    # 用来获取类的唯一实例
    # 同一个进程中只存在唯一的实例
    @classmethod
    def get_instance(cls):
        # 双重检查锁确保线程安全
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:

                    # 绕过 __new__ 的异常，直接创建实例
                    instance = super().__new__(cls)
                    instance.__init__()
                    cls._instance = instance
        return cls._instance


    def submit_pipeline(self, pipeline, config=None, generate_func=None):
        from sage.core.graph import SageGraph
        graph = SageGraph(pipeline, config)
        self.graphs[graph.name] = graph  # 存储图到字典中
        # 合并配置
        if config:
            graph.config.update(config)
        try:
            self.logger.info(f"Received graph '{graph.name}' with {len(graph.nodes)} nodes")
            # 编译图
            dag = self.compiler.compile_graph(graph)
            self.dags[dag.name] = dag  # 存储 DAG 到字典中
            self.logger.info(f"Graph '{graph.name}' submitted to runtime manager.")
            # 通过运行时管理器获取对应平台的运行时并提交任务
            task_handle = self.runtime_manager.submit(dag) 
        except Exception as e:
            self.logger.info(f"Failed to submit graph '{graph.name}': {e}")
            raise
    
    def submit_mixed_pipeline(self, pipeline, config=None):
        from sage.core.graph import SageGraph
        graph = SageGraph(pipeline, config)
        self.graphs[graph.name] = graph
        if config:
            graph.config.update(config)
        try:
            self.logger.info(f"Received mixed graph '{graph.name}' with {len(graph.nodes)} nodes")
            # 编译图
            mixed_dag = MixedDAG(graph)
            self.dags[mixed_dag.name] = mixed_dag  # 存储 DAG 到字典中
            mixed_dag.run()
            self.logger.info(f"Mixed graph '{graph.name}' submitted to runtime manager.")
        except Exception as e:
            self.logger.info(f"Failed to submit graph '{graph.name}': {e}")
            raise