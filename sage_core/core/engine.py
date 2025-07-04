# from sage.core.compiler.query_compiler import QueryCompiler
from sage_core.api.env import BaseEnvironment
from sage_runtime.mixed_dag import MixedDAG
from sage_runtime.runtime_manager import RuntimeManager
from sage_utils.custom_logger import CustomLogger
import threading


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
        # self.compiler= QueryCompiler()
        from sage_core.core.compiler import Compiler
        self.graphs:dict[str, Compiler] = {}  # 存储 pipeline 名称到 SageGraph 的映射
        self.env_to_dag:dict = {} # 存储name到dag的映射，其中dag的类型为DAG或RayDAG

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
    
    def submit_env(self, env:BaseEnvironment):
        from sage_core.core.compiler import Compiler
        graph = Compiler(env)
        graph.debug_print_graph()
        self.graphs[graph.name] = graph
        try:
            self.logger.info(f"Received mixed graph '{graph.name}' with {len(graph.nodes)} nodes")
            # 编译图
            mixed_dag = MixedDAG(graph)
            self.env_to_dag[env.name] = mixed_dag  # 存储 DAG 到字典中
            mixed_dag.submit()
            self.logger.info(f"Mixed graph '{graph.name}' submitted to runtime manager.")
        except Exception as e:
            self.logger.info(f"Failed to submit graph '{graph.name}': {e}")
            raise
    
    def run_once(self, env:BaseEnvironment, node:str = None):
        """
        执行一次环境的 DAG
        """
        self.logger.info(f"Executing DAG for environment '{env.name}'")
        dag = self.env_to_dag.get(env.name)
        self.logger.debug(f"Found DAG for environment '{env.name}': {dag}")
        dag.execute_once()
        self.logger.info(f"DAG for environment '{env.name}' have completed execution.")

    def run_streaming(self, env:BaseEnvironment, node:str = None):
        """
        执行一次环境的 DAG
        """
        self.logger.info(f"Executing streaming DAG for environment '{env.name}'")
        dag = self.env_to_dag.get(env.name)
        dag.execute_streaming()
        self.logger.info(f"Streaming DAG for environment '{env.name}' have started.")
