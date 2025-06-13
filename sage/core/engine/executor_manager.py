import logging



from sage.core.engine.executor import StreamingTaskExecutor, OneshotTaskExecutor, BaseTaskExecutor
from sage.core.engine.scheduling_strategy import SchedulingStrategy, ResourceAwareStrategy, PriorityStrategy
from sage.core.dag.dag import DAG
from sage.core.dag.dag_manager import DAGManager
from sage.core.engine.slot import Slot
from sage.core.dag.dag_node import BaseDAGNode,ContinuousDAGNode,OneShotDAGNode
from sage.core.engine.execution_backend import ExecutionBackend, LocalExecutionBackend, RayExecutionBackend
import time

class ExecutorManager:
    """用于管理任务，初始化slots,并负责将任务提交到slot里面运行，基于已提交的dag提取出所有的node并根据node按照一定的策略分配给不同的slot
     Attributes:
        available_slots (List[Slot]): 可用计算槽位列表
        max_slots (int): 最大槽位数量
        dag_manager (DAGManager): DAG流程管理器
        task_to_slot (Dict[object, int]): 任务到槽位的映射关系
        dag_to_tasks (Dict[str, List[object]]): DAG到其关联任务的映射
        logger (logging.Logger): 日志记录器
        scheduling_strategy (SchedulingStrategy): 任务调度策略实现
    """
    def __init__(self,dag_manager:DAGManager, max_slots=4,scheduling_strategy=None):
        self.dag_manager = dag_manager
        self.dag_to_tasks={}
        self.task_handles = {}  # dag_id -> [task_handles]
        self.logger=logging.getLogger(__name__)
        self.local_backend = LocalExecutionBackend(max_slots, scheduling_strategy)
        self.ray_backend = RayExecutionBackend()

        # self.available_slots = [Slot(slot_id=i) for i in range(max_slots)]
        # self.max_slots = max_slots
        # self.task_to_slot ={}
        # if scheduling_strategy is None:
        #     self.scheduling_strategy = ResourceAwareStrategy()
        # elif scheduling_strategy.lower() =="prioritystrategy":
        #     self.scheduling_strategy = PriorityStrategy({})
        # else :
        #     self.scheduling_strategy = ResourceAwareStrategy()


    def run_dags(self):
        # """
        # 提交DAG并调度其节点

        # 流程：
        # 1. 从DAG管理器获取正在运行的DAG列表
        # 2. 清空管理器的运行中DAG记录（避免重复提交）
        # 3. 对每个DAG创建对应任务：
        #    - 流式DAG：为每个节点创建独立任务
        #    - 一次性DAG：为整个DAG创建单个任务
        # 4. 将任务分配到可用槽位执行
        # """
        """
        执行所有待运行的DAG
        根据DAG配置选择不同的执行后端
        """
        running_dags=self.dag_manager.get_running_dags()
        self.dag_manager.clear_running_dags()
        for dag_id in running_dags:
            self.task_handles[dag_id] = []
            dag = self.dag_manager.get_dag(dag_id)
            
            # 根据DAG配置选择执行后端
            execution_backend = self._get_execution_backend(dag)
            
            if dag.strategy == "streaming":
                self._execute_streaming_dag(dag_id, dag, execution_backend)
            else:
                self._execute_oneshot_dag(dag_id, dag, execution_backend)
        
        # for dag_id in running_dags:
        #     self.task_handles[dag_id] = []
        #     dag = self.dag_manager.get_dag(dag_id)
                
        #     if self.dag_to_tasks.get(dag_id) is None :
        #         self.dag_to_tasks[dag_id]=[]
        #         dag=self.dag_manager.get_dag(dag_id)
        #         if dag.strategy=="streaming" :
        #             working_config=dag.working_config
        #             for node in dag.nodes:
        #                 streaming_task=self.create_streaming_task(node,working_config)
        #                 slot_id=self.schedule_task(streaming_task)
        #                 self.dag_to_tasks[dag_id].append(streaming_task)
        #                 self.task_to_slot[streaming_task]=slot_id
        #                 self.available_slots[slot_id].submit_task(streaming_task)
        #                 self.logger.debug(f"{node.name} submitted task for slot {slot_id}")
        #         else :
        #             task=self.create_oneshot_task(dag)
        #             # slot_id=self.schedule_task(task)
        #             # self.dag_to_tasks[dag_id].append(task)
        #             # self.task_to_slot[task]=slot_id
        #             # self.available_slots[slot_id].submit_task(task)
        #             # self.logger.debug(f"dag submitted task for slot {slot_id}")
        #             task.execute()

    def _get_execution_backend(self, dag: DAG) -> ExecutionBackend:
        """根据DAG配置选择执行后端"""
        # 检查DAG配置中的执行后端设置
        backend_type = dag.working_config.get('execution_backend', 'local')
        
        if backend_type == 'ray':
            self.logger.info(f"Using Ray backend for DAG {dag.dag_id}")
            return self.ray_backend
        else:
            self.logger.info(f"Using local backend for DAG {dag.dag_id}")
            return self.local_backend
    
    def _execute_streaming_dag(self, dag_id: int, dag: DAG, backend: ExecutionBackend):
        """使用指定后端执行流式DAG"""
        for node in dag.nodes:
            task = StreamingTaskExecutor(node, dag.working_config)
            task_handle = backend.submit_task(task)
            self.task_handles[dag_id].append(task_handle)
            self.logger.debug(f"{node.name} submitted to {backend.__class__.__name__}")
    
    def _execute_oneshot_dag(self, dag_id: int, dag: DAG, backend: ExecutionBackend):
        """使用指定后端执行一次性DAG"""
        task = OneshotTaskExecutor(dag)
        
        if isinstance(backend, RayExecutionBackend):
            # Ray执行
            task_handle = backend.submit_task(task)
            self.task_handles[dag_id].append(task_handle)
        else:
            # 本地执行，直接调用execute
            task.execute()
    
    def stop_dag(self, dag_id: int):
        """停止指定DAG的所有任务"""
        if dag_id not in self.task_handles:
            return
        
        dag = self.dag_manager.get_dag(dag_id)
        backend = self._get_execution_backend(dag)
        
        # 停止所有任务
        for task_handle in self.task_handles[dag_id]:
            backend.stop_task(task_handle)
        
        # 清理记录
        del self.task_handles[dag_id]
        self.dag_manager.remove_from_running(dag_id)
    
    def get_dag_status(self, dag_id: int):
        """获取DAG执行状态"""
        if dag_id not in self.task_handles:
            return {"status": "not_found"}
        
        dag = self.dag_manager.get_dag(dag_id)
        backend = self._get_execution_backend(dag)
        
        task_statuses = []
        for task_handle in self.task_handles[dag_id]:
            status = backend.get_status(task_handle)
            task_statuses.append(status)
        
        return {
            "dag_id": dag_id,
            "backend": backend.__class__.__name__,
            "task_count": len(task_statuses),
            "tasks": task_statuses
        }

    # def schedule_task(self, task: BaseTaskExecutor) -> int :
    #         """
    #            调度任务到指定槽位

    #            Args:
    #                task: 需要调度的任务对象

    #            Returns:
    #                int: 分配的槽位ID

    #            Raises:
    #                RuntimeError: 当无可用槽位时抛出
    #            """
    #         selected_slot_id = self.scheduling_strategy.select_slot(
    #             task, self.available_slots
    #         )
    #         self.logger.info(f"chosen slot id {selected_slot_id}")
    #         if selected_slot_id > 0 :
    #             self.available_slots[selected_slot_id].submit_task(task)
    #             self.task_to_slot[task] = selected_slot_id
    #         return selected_slot_id


