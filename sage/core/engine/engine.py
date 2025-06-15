from sage.core.engine.executor_manager import ExecutorManager
from sage.core.dag.dag_manager import DAGManager
from sage.core.compiler.query_compiler import QueryCompiler
import threading


class Engine:
    _instance = None
    dag_manager: DAGManager
    executor_manager: ExecutorManager
    compiler: QueryCompiler
    pipeline_to_dag: dict
    _lock = threading.Lock()

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

    def __init__(self,generate_func = None):
        # 确保只初始化一次
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        # 初始化各管理器（确保单例）
        self.dag_manager=DAGManager()
        self.executor_manager = ExecutorManager(dag_manager=self.dag_manager)
        self.compiler= QueryCompiler(generate_func=generate_func)
        self.pipeline_to_dag = {}

    def submit_pipeline(self,pipeline,config=None):
        optimized_dag = self.compiler.compile(pipeline,config)
        # execution_type和node_mapping被封装进dag里边当成员变量了
        dag_id=self.dag_manager.add_dag(optimized_dag)
        self.pipeline_to_dag[pipeline]=dag_id
        self.dag_manager.submit_dag(dag_id)
        self.executor_manager.run_dags()

    def submit_graph(self, graph):
        dag = self.compiler.compile_graph(graph)
        dag_id=self.dag_manager.add_dag(dag)
        self.dag_manager.submit_dag(dag_id)
        self.executor_manager.run_dags()
    

    def stop_pipeline(self,pipeline):
        dag_id=self.pipeline_to_dag[pipeline]
        self.executor_manager.stop_dag(dag_id)


    def get_executor_manager(self):
        return self.executor_manager


    def get_dag_manager(self):
        return self.dag_manager