# from sage.core.engine.executor_manager import ExecutorManager
from sage.core.dag.dag_manager import DAGManager
from sage.core.compiler.query_compiler import QueryCompiler
from sage.core.runtime.runtime_manager import RuntimeManager
import threading, typing, logging

class Engine:
    _instance = None
    def __init__(self,generate_func = None):
        # 确保只初始化一次
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.dag_manager = DAGManager()
        self.runtime_manager = RuntimeManager()
        self.compiler= QueryCompiler(generate_func=generate_func)
        self._lock = threading.Lock()
        self.logger = logging.getLogger("Engine")
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


    

    def submit_graph(self, graph):
        """
        根据图配置提交到合适的后端执行
        
        Args:
            graph: SageGraph 实例
            
        Returns:
            str: 任务句柄
        """
        try:
            self.logger.info(f"Received graph '{graph.name}' with {len(graph.nodes)} nodes")
            
            # 验证图的有效性
            if not graph.validate_graph():
                raise ValueError(f"Invalid graph: {graph.name}")
            # 编译图
            compiled_task = self.compiler.compile_graph(graph)
            self.logger.info(f"Graph '{graph.name}' submitted to runtime manager.")
            # 通过运行时管理器获取对应平台的运行时并提交任务
            task_handle = self.runtime_manager.submit(compiled_task) 
        except Exception as e:
            self.logger.info(f"Failed to submit graph '{graph.name}': {e}")
            raise