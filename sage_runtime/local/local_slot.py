import logging
from concurrent.futures import ThreadPoolExecutor

# from sage_runtime.local.local_dag_node import LocalDAGNode

class Slot:
    """
        计算槽位资源管理器，负责管理线程池和任务生命周期

        Attributes:
            slot_id (int): 槽位唯一标识
            thread_pool (ThreadPoolExecutor): 线程池对象
            running_tasks (List[StreamingTask]): 正在运行的任务列表
            current_load (int): 当前槽位负载（运行中的线程数）
            task_to_future (Dict[StreamingTask, Future]): 任务到 Future 的映射
            max_load (int): 最大允许负载（最大任务数）
            logger (logging.Logger): 日志记录器
        """
    def __init__(self, slot_id: int,max_threads=300):
        self.slot_id = slot_id
        self.thread_pool = ThreadPoolExecutor(
            max_workers=max_threads,
            thread_name_prefix=f"Slot-{slot_id}"
        )
        self.running_tasks=[] #正在运行的任务
        self.current_load = 0 #当前slot的负载
        self.task_to_future={}
        self.max_load = max_threads
        self.logger=logging.getLogger(__name__)

    def submit_task(self, task) -> bool:
        """
               提交任务到线程池

               Args:
                   task: 需要执行的流式任务对象

               Returns:
                   bool: 是否成功提交
                         - True: 任务已加入队列
                         - False: 任务已存在或超出负载限制
        """
        #提交一个task并进入线程队列等待分配线程
        self.clear_tasks()
        if task in self.running_tasks:
            return False
        if self.current_load < self.max_load:
            # task被真正执行的地方
            future=self.thread_pool.submit(task.run_loop)
            self.task_to_future[task]=future
            self.running_tasks.append(task)
            self.current_load += 1
            self.task_to_future[task]=future
            return True
        return False

    def clear_tasks(self):
        #清除所有已经完成的任务
        """清理已完成的任务，维护运行状态"""
        completed_tasks = [task for task, future in self.task_to_future.items() if future.done()]
        for task in completed_tasks:
            self.task_to_future.pop(task, None)
            if task in self.running_tasks:
                self.running_tasks.remove(task)
            self.current_load = max(0, self.current_load - 1)

    def adjust_capacity(self, new_max: int):
        self.max_load = new_max

    def stop(self,task):
        #停止一个task的执行
        try :
            if task not in self.running_tasks:
                return
            else :
                future = self.task_to_future[task]
                if future.done():
                    return
                if not future.running() :
                    future.cancel()
                else :
                    task.stop()
                    result=future.result(timeout=3)
                    self.logger.debug(f"{task.node.name} stopped successfully")
                    self.running_tasks.remove(task)
                    self.task_to_future.pop(task)
                    self.current_load -= 1
        except Exception as e:
            self.logger.error(f"stop task failed: {e}")
            raise RuntimeError(f"stop task failed: {e}")

    def shutdown(self):
        # 停止所有任务
        for task in list(self.running_tasks):
            try:
                self.stop(task)
            except Exception as e:
                self.logger.error(f"Failed to stop task : {e}")
        # 再关闭线程池
        self.thread_pool.shutdown(wait=True)
        self.running_tasks.clear()
        self.task_to_future.clear()
        self.current_load = 0

    def get_load(self):
        """
                获取当前有效负载

                Returns:
                    int: 当前活跃线程数（清理后）
                """
        self.clear_tasks()
        return self.current_load
