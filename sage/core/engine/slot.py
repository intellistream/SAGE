import logging
from concurrent.futures import ThreadPoolExecutor
from sage.core.engine.executor import StreamingExecutor
from sage.core.dag.dag_node import BaseDAGNode


class Slot:
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
        #提交一个task并进入线程队列等待分配线程
        self.clear_tasks()
        if task in self.running_tasks:
            return False
        if self.current_load < self.max_load:
            future=self.thread_pool.submit(task.execute)
            self.task_to_future[task]=future
            self.running_tasks.append(task)
            self.current_load += 1
            self.task_to_future[task]=future
            return True
        return False

    def clear_tasks(self):
        #清除所有已经完成的任务
        completed_tasks = [task for task, future in self.task_to_future.items() if future.done()]
        for task in completed_tasks:
            self.task_to_future.pop(task, None)
            if task in self.running_tasks:
                self.running_tasks.remove(task)
            self.current_load = max(0, self.current_load - 1)

    def adjust_capacity(self, new_max: int):
        self.max_load = new_max

    def stop(self,task:StreamingExecutor):
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
        # 先停止所有任务
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
        self.clear_tasks()
        return self.current_load
