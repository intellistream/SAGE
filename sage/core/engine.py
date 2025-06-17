# from sage.core.engine.executor_manager import ExecutorManager
from sage.core.dag.dag_manager import DAGManager
from sage.core.compiler.query_compiler import QueryCompiler
from sage.core.runtime.ray.ray_runtime import RayRuntime
from sage.core.runtime.local.local_runtime import LocalRuntime
from sage.core.runtime.local.local_task import StreamingTask, OneshotTask, BaseTask
import threading, typing, logging


class Engine:
    _instance = None
    dag_manager: DAGManager
    # executor_manager: ExecutorManager
    compiler: QueryCompiler
    pipeline_to_dag: dict
    _lock = threading.Lock()
    _ray_backend: RayRuntime = None
    _local_backend: LocalRuntime = None
    logger: logging.Logger
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
        # self.executor_manager = ExecutorManager(dag_manager=self.dag_manager)
        self.compiler= QueryCompiler(generate_func=generate_func)
        self.logger = logging.getLogger(__name__)

        self.pipeline_to_dag = {}

    def get_dag_manager(self):
        return self.dag_manager
    


    def submit_graph(self, graph) -> str:
        """
        根据图配置提交到合适的后端执行
        
        Args:
            graph: SageGraph 实例
            
        Returns:
            str: 任务句柄
        """
        try:
            print(f"[Engine] Received graph '{graph.name}' with {len(graph.nodes)} nodes")
            
            # 验证图的有效性
            if not graph.validate_graph():
                raise ValueError(f"Invalid graph: {graph.name}")
            
            # 获取平台配置
            platform = graph.config.get("platform", "local").lower()
            print(f"[Engine] Graph platform: {platform}")
            
            # 编译图
            if platform == "ray":
                task_handle = self._submit_to_ray_backend(graph)
            elif platform == "local":
                task_handle = self._submit_to_local_backend(graph)
            else:
                raise ValueError(f"Unsupported platform: {platform}")
            
            print(f"[Engine] Graph '{graph.name}' submitted with handle: {task_handle}")
            return task_handle
            
        except Exception as e:
            print(f"[Engine] Failed to submit graph '{graph.name}': {e}")
            raise


    def _submit_to_ray_backend(self, graph) -> str:
        """
        提交到 Ray 后端执行
        
        Args:
            graph: SageGraph 实例
            
        Returns:
            str: 任务句柄
        """
        # 编译为 Ray DAG Task
        ray_dag_task = self.compiler.compile_graph(graph)
        
        # 初始化 Ray 后端（如果还没有）
        if self._ray_backend is None:
            self._ray_backend = RayRuntime(monitoring_interval=2.0)
            print("[Engine] Initialized Ray DAG execution backend")
        
        # 提交任务
        task_handle = self._ray_backend.submit_task(ray_dag_task)
        
        # 存储任务信息
        # self.running_tasks[task_handle] = {
        #     'type': 'ray_dag',
        #     'platform': 'ray',
        #     'graph': graph,
        #     'task': ray_dag_task,
        #     'backend': self._ray_backend
        # }
        
        print(f"[Engine] Graph '{graph.name}' submitted to Ray backend with handle: {task_handle}")
        return task_handle

    def _submit_to_local_backend(self, graph) -> str:
        """
        提交到本地后端执行
        
        Args:
            graph: SageGraph 实例
            
        Returns:
            str: 任务句柄
        """
        # 编译为本地 DAG
        local_dag = self.compiler.compile_graph(graph)
        
        # 初始化本地后端（如果还没有）
        if self._local_backend is None:
            self._local_backend = LocalRuntime(max_slots=4)
            print("[Engine] Initialized local execution backend")
        
        # 将 DAG 包装为任务
        # local_dag_task = self._create_local_dag_task(local_dag)


        # optimized_dag = self.compiler.compile(pipeline,config)
        # execution_type和node_mapping被封装进dag里边当成员变量了
        self.local_backend = LocalRuntime(max_slots = 4, scheduling_strategy = None)

        for node in local_dag.nodes:

            task = StreamingTask(node, local_dag.working_config)
            task_handle = self.local_backend.submit_task(task)
            #self.task_handles[dag_id].append(task_handle)
            self.logger.debug(f"{node.name} submitted to {self.local_backend.__class__.__name__}")
        # 提交任务
        # task_handle = self._local_backend.submit_task(local_dag_task)
        
        # # 存储任务信息
        # self.running_tasks[task_handle] = {
        #     'type': 'local_dag',
        #     'platform': 'local',
        #     'graph': graph,
        #     'dag': local_dag,
        #     'task': local_dag_task,
        #     'backend': self._local_backend
        # }
        
        print(f"[Engine] Graph '{graph.name}' submitted to local backend with handle: {task_handle}")
        return task_handle