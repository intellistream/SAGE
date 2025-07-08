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
        self.DAGs: dict[str, Compiler] = {}  # 存储 pipeline 名称到 SageGraph 的映射
        self.env_to_dag: dict[str, MixedDAG] = {}  # 存储name到dag的映射，其中dag的类型为DAG或RayDAG
        # print("Engine initialized")
        self.logger = CustomLogger(
            filename=f"SageEngine",
            console_output="DEBUG",
            file_output=True,
            global_output="WARNING",
            name="SageEngine"
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

    def submit_env(self, env: BaseEnvironment):
        from sage_core.core.compiler import Compiler
        # env, graph和dag用的都是同一个名字
        graph = Compiler(env)
        graph.debug_print_graph()
        self.DAGs[graph.name] = graph
        try:
            self.logger.info(f"Received mixed graph '{graph.name}' with {len(graph.nodes)} nodes")
            # 编译图
            mixed_dag = MixedDAG(graph, env)
            self.env_to_dag[env.name] = mixed_dag  # 存储 DAG 到字典中
            mixed_dag.submit()
            self.logger.info(f"Mixed graph '{graph.name}' submitted to runtime manager.")
        except Exception as e:
            self.logger.info(f"Failed to submit graph '{graph.name}': {e}")
            raise

    def run_once(self, env: BaseEnvironment, node: str = None):
        """
        执行一次环境的 DAG
        """
        self.logger.info(f"Executing DAG for environment '{env.name}'")
        dag = self.env_to_dag.get(env.name)
        self.logger.debug(f"Found DAG for environment '{env.name}': {dag}")
        dag.execute_once()
        self.logger.info(f"DAG for environment '{env.name}' have completed execution.")

    def run_streaming(self, env: BaseEnvironment, node: str = None):
        """
        执行一次环境的 DAG
        """
        self.logger.info(f"Executing streaming DAG for environment '{env.name}'")
        dag = self.env_to_dag.get(env.name)
        dag.execute_streaming()
        self.logger.info(f"Streaming DAG for environment '{env.name}' have started.")

    def stop_pipeline(self, env: BaseEnvironment):
        """
        停止指定环境的 DAG
        """
        self.logger.info(f"Stopping DAG for environment '{env.name}'")
        dag = self.env_to_dag.get(env.name)
        if dag:
            dag.stop()
            self.logger.info(f"DAG for environment '{env.name}' has been stopped.")
        else:
            self.logger.warning(f"No DAG found for environment '{env.name}'")

    def close_pipeline(self, env: BaseEnvironment):
        """
        停止指定环境的 DAG
        """
        self.logger.info(f"Stopping DAG for environment '{env.name}'")
        graph = self.graphs.pop(env.name, None)
        if graph:
            # graph.destroy()
            self.logger.info(f"Graph for environment '{env.name}' has been destroyed.")
        
        dag = self.env_to_dag.pop(env.name, None)
        if dag:
            dag.stop()
            self.logger.info(f"DAG for environment '{env.name}' has been stopped.")
        else:
            self.logger.warning(f"No DAG found for environment '{env.name}'")
        # 如果没有剩余环境，执行完整 shutdown
        if not self.env_to_dag:
            self.shutdown()

    def shutdown(self):
        """
        完整释放 Engine 持有的所有资源：
        - 停掉 RuntimeManager（线程、Ray actor 等）
        - 停掉可能的 TCP/HTTP server
        - 清空 DAG 映射与缓存
        - 重置 Engine 单例
        """
        self.logger.info("Shutting down Engine and releasing resources")
        try:
            self.runtime_manager.shutdown_all()
        except Exception:
            self.logger.exception("Error shutting down RuntimeManager")

        self.env_to_dag.clear()
        self.DAGs.clear()

        Engine._instance = None
        self.logger.info("Engine shutdown complete")
