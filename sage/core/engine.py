from typing import Type, TYPE_CHECKING, Union, Any, TYPE_CHECKING
from sage.core.compiler.query_compiler import QueryCompiler
from sage.core.runtime.runtime_manager import RuntimeManager

import threading, typing, logging

class Engine:
    _instance = None
    _lock = threading.Lock()
    def __init__(self,generate_func = None):
        # 确保只初始化一次
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        # self.dag_manager = DAGManager() # deprecated
        self.runtime_manager = RuntimeManager()
        self.compiler= QueryCompiler(generate_func=generate_func)
        self.logger = logging.getLogger("Engine")
        from sage.core.graph import SageGraph
        self.graphs:dict[str, SageGraph] = {}  # 存储 pipeline 名称到 SageGraph 的映射
        self.dags:dict = {} # 存储name到dag的映射，其中dag的类型为DAG或RayDAG

    def __new__(cls):
        # 禁止直接实例化
        raise RuntimeError("请通过 get_instance() 方法获取实例")

    # 用来获取类的唯一实例
    # 同一个进程中只存在唯一的实例
    @classmethod
    def get_instance(cls,generate_func):
        # 双重检查锁确保线程安全
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:

                    # 绕过 __new__ 的异常，直接创建实例
                    instance = super().__new__(cls)
                    instance.__init__(generate_func)
                    cls._instance = instance
        return cls._instance


    def submit_pipeline(self, pipeline, config=None, generate_func=None):
        from sage.core.graph import SageGraph
        graph = SageGraph(pipeline, config)
        print(pipeline.use_ray)
        print(config)
        print (graph.config)
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