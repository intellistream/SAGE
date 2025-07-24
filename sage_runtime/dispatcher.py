import os
import time
from typing import Dict, List, Any, Tuple, Union, TYPE_CHECKING
from sage_runtime.task.base_task import BaseTask
from sage_utils.actor_wrapper import ActorWrapper
from sage_runtime.router.connection import Connection
from sage_utils.custom_logger import CustomLogger
import ray
from ray.actor import ActorHandle

from sage_utils.ray_init_helper import ensure_ray_initialized
if TYPE_CHECKING:
    from sage_core.environment.base_environment import BaseEnvironment 
    from sage_jobmanager.execution_graph import ExecutionGraph, GraphNode

# 这个dispatcher可以直接打包传给ray sage daemon service
class Dispatcher():
    def __init__(self, graph: 'ExecutionGraph', env:'BaseEnvironment'):
        self.total_stop_signals = graph.total_stop_signals
        self.received_stop_signals = 0
        self.graph = graph
        self.env = env
        self.name:str = env.name
        self.remote = env.platform == "remote"
        self.logger = CustomLogger([
                ("console", "INFO"),  # 控制台显示重要信息
                (os.path.join(env.env_base_dir, "Dispatcher.log"), "DEBUG"),  # 详细日志
                (os.path.join(env.env_base_dir, "Error.log"), "ERROR")  # 错误日志
            ],
            name = f"Environment_{self.name}",
        )
        # self.nodes: Dict[str, Union[ActorHandle, LocalDAGNode]] = {}
        self.tasks: Dict[str, Union[BaseTask, ActorWrapper]] = {}
        self.is_running: bool = False
        self.logger.info(f"Dispatcher '{self.name}' construction complete")
        if env.platform is "remote":
            ensure_ray_initialized()
        self.setup_logging_system()

    def receive_stop_signal(self):
        """
        接收停止信号并处理
        """
        self.logger.info(f"Dispatcher received stop signal.")
        self.received_stop_signals += 1
        if self.received_stop_signals >= self.total_stop_signals:
            self.logger.info(f"Received all {self.total_stop_signals} stop signals, stopping dispatcher for batch job.")
            self.cleanup()
            return True
        else:
            return False


    def setup_logging_system(self): 
        self.logger = CustomLogger([
                ("console", "INFO"),  # 控制台显示重要信息
                (os.path.join(self.env.env_base_dir, "Dispatcher.log"), "DEBUG"),  # 详细日志
                (os.path.join(self.env.env_base_dir, "Error.log"), "ERROR")  # 错误日志
            ],
            name = f"Dispatcher_{self.name}",
        )

    def start(self):
        # 第三步：提交所有节点开始运行
        for node_name, task in self.tasks.items():
            try:
                task.start_running()
                self.logger.debug(f"Started node: {node_name}")
            except Exception as e:
                self.logger.error(f"Failed to start node {node_name}: {e}", exc_info=True)
        self.logger.info(f"Job submission completed: {len(self.tasks)} nodes")
        self.is_running = True

    # Dispatcher will submit the job to LocalEngine or Ray Server.    
    def submit(self):
        """编译图结构，创建节点并建立连接"""
        self.logger.info(f"Compiling Job for graph: {self.name}")
        
        # 第一步：创建所有节点实例
        for node_name, graph_node in self.graph.nodes.items():
            # task = graph_node.create_dag_node()
            task = graph_node.transformation.task_factory.create_task(graph_node.name, graph_node.ctx)

            self.tasks[node_name] = task

            self.logger.debug(f"Added node '{node_name}' of type '{task.__class__.__name__}'")
        
        # 第二步：建立节点间的连接
        for node_name, graph_node in self.graph.nodes.items():
            self._setup_node_connections(node_name, graph_node)
        self.start()



    def _setup_node_connections(self, node_name: str, graph_node: 'GraphNode'):
        """
        为节点设置下游连接
        
        Args:
            node_name: 节点名称
            graph_node: 图节点对象
        """
        output_handle = self.tasks[node_name]
        
        for broadcast_index, parallel_edges in enumerate(graph_node.output_channels):
            for parallel_index, parallel_edge in enumerate(parallel_edges):
                target_name = parallel_edge.downstream_node.name
                target_input_index = parallel_edge.input_index
                target_handle = self.tasks[target_name]

                connection = Connection(
                    broadcast_index=broadcast_index,
                    parallel_index=parallel_index,
                    target_name=target_name,
                    target_handle=target_handle.get_object(),
                    target_input_index = target_input_index,
                    target_type="local"
                )
                try:
                    output_handle.add_connection(connection)
                    self.logger.debug(f"Setup connection: {node_name} -> {target_name}")
                    
                except Exception as e:
                    self.logger.error(f"Error setting up connection {node_name} -> {target_name}: {e}", exc_info=True)

    def stop(self):
        """停止所有任务"""
        if not self.is_running:
            self.logger.warning("Dispatcher is not running")
            return
            
        self.logger.info(f"Stopping dispatcher '{self.name}'")
        
        # 发送停止信号给所有任务
        for node_name, node_instance in self.tasks.items():
            try:
                node_instance.stop()
                self.logger.debug(f"Sent stop signal to node: {node_name}")
            except Exception as e:
                self.logger.error(f"Error stopping node {node_name}: {e}")
        
        # 等待所有任务停止（最多等待10秒）
        self._wait_for_tasks_stop(timeout=10.0)
        
        self.is_running = False
        self.logger.info("Dispatcher stopped")

    def _wait_for_tasks_stop(self, timeout: float = 10.0):
        """等待所有任务停止"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            all_stopped = True
            
            for node_name, task in self.tasks.items():
                if hasattr(task, 'is_running') and task.is_running:
                    all_stopped = False
                    break
            
            if all_stopped:
                self.logger.debug("All tasks stopped")
                return
                
            time.sleep(0.1)
        
        self.logger.warning(f"Timeout waiting for tasks to stop after {timeout}s")

    def cleanup(self):
        """清理所有资源"""
        self.logger.info(f"Cleaning up dispatcher '{self.name}'")
        
        try:
            # 停止所有任务
            if self.is_running:
                self.stop()
            
            if self.remote:
                # 清理 Ray Actors
                self._cleanup_ray_actors()
            else:
                # 清理任务引用
                for node_name, task in self.tasks.items():
                    try:
                        task.cleanup()
                        self.logger.debug(f"Cleaned up task: {node_name}")
                    except Exception as e:
                        self.logger.error(f"Error cleaning up task {node_name}: {e}")
            # 清空任务字典
            self.tasks.clear()
            
            self.logger.info("Dispatcher cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during dispatcher cleanup: {e}")

    def _cleanup_ray_actors(self):
        """清理所有Ray Actor"""
        if not self.tasks:
            return

        self.logger.info(f"Cleaning up {len(self.tasks)} actors...")

        # 使用ActorWrapper的cleanup_and_kill方法
        cleanup_results = []
        for task_id, actor_wrapper in self.tasks.items():
            try:
                if hasattr(actor_wrapper, 'cleanup_and_kill'):
                    # 使用ActorWrapper的封装方法
                    cleanup_success, kill_success = actor_wrapper.cleanup_and_kill(
                        cleanup_timeout=5.0, 
                        no_restart=True
                    )
                    cleanup_results.append((task_id, cleanup_success, kill_success))
                    
                    if kill_success:
                        self.logger.debug(f"Successfully killed actor for task {task_id}")
                    else:
                        self.logger.warning(f"Failed to kill actor for task {task_id}")
                else:
                    # 备用方案：直接使用kill_actor方法
                    if hasattr(actor_wrapper, 'kill_actor'):
                        kill_success = actor_wrapper.kill_actor(no_restart=True)
                        cleanup_results.append((task_id, False, kill_success))
                    else:
                        self.logger.warning(f"ActorWrapper for task {task_id} does not support kill operations")
                        cleanup_results.append((task_id, False, False))
                        
            except Exception as e:
                self.logger.warning(f"Error during cleanup for task {task_id}: {e}")
                cleanup_results.append((task_id, False, False))

        # 报告清理结果
        successful_cleanups = sum(1 for _, cleanup_success, _ in cleanup_results if cleanup_success)
        successful_kills = sum(1 for _, _, kill_success in cleanup_results if kill_success)
        
        if successful_kills == len(self.tasks):
            self.logger.info(f"Successfully cleaned up all {len(self.tasks)} actors")
        else:
            self.logger.warning(f"Cleanup completed: {successful_cleanups}/{len(self.tasks)} cleanups, {successful_kills}/{len(self.tasks)} kills successful")

    def _wait_for_cleanup_completion(self, cleanup_futures: List[Tuple[Any, Any]], timeout: float = 5.0):
        """
        等待清理操作完成 (已弃用)
        此方法现在不再使用，因为我们使用ActorWrapper.cleanup_and_kill()方法
        """
        self.logger.debug("_wait_for_cleanup_completion is deprecated, cleanup is now handled by ActorWrapper")
        pass


    def get_task_status(self) -> Dict[str, Any]:
        """获取所有任务的状态"""
        status = {}
        
        for node_name, task in self.tasks.items():
            try:
                task_status = {
                    "name": node_name,
                    "running": getattr(task, 'is_running', False),
                    "processed_count": getattr(task, '_processed_count', 0),
                    "error_count": getattr(task, '_error_count', 0),
                }
                status[node_name] = task_status
            except Exception as e:
                status[node_name] = {
                    "name": node_name,
                    "error": str(e)
                }
        
        return status


    def get_statistics(self) -> Dict[str, Any]:
        """获取dispatcher统计信息"""
        return {
            "name": self.name,
            "is_running": self.is_running,
            "task_count": len(self.tasks),
            "task_status": self.get_task_status()
        }