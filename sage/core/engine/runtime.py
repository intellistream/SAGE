from sage.core.engine.executor_manager import ExecutorManager
from sage.core.dag.dag_manager import DAGManager
from sage.core.compiler.query_compiler import QueryCompiler
import threading


class Engine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        # 禁止直接实例化
        raise RuntimeError("请通过 get_instance() 方法获取实例")

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

    def __init__(self):
        # 确保只初始化一次
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        # 初始化各管理器（确保单例）
        self.dag_manager=DAGManager()
        self.executor_manager = ExecutorManager(dag_manager=self.dag_manager)
        self.compiler= QueryCompiler()
        self.pipeline_id = {}

    def submit_pipeline(self,pipeline,config=None):
        optimized_dag, execution_type,node_mapping = self.compiler.compile(pipeline=pipeline)
        if config.get("is_long_running", False):
            optimized_dag.strategy="streaming"
        else :
            optimized_dag.strategy="oneshot"
        optimized_dag.working_config=config
        dag_id=self.dag_manager.add_dag(optimized_dag)
        optimized_dag.dag_id=dag_id
        self.pipeline_id[pipeline]=dag_id
        self.dag_manager.submit_dag(dag_id)
        self.executor_manager.submit_dag()

    def stop_pipeline(self,pipeline):
        dag_id=self.pipeline_id[pipeline]
        self.executor_manager.stop_dag(dag_id)


    def get_executor_manager(self):
        return self.executor_manager


    def get_dag_manager(self):
        return self.dag_manager