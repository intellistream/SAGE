import os
import time
from typing import Dict, List, Any, Tuple, Union, TYPE_CHECKING
from sage.runtime.service.base_service_task import BaseServiceTask
from sage.runtime.task.base_task import BaseTask
from sage.utils.actor_wrapper import ActorWrapper
from sage.runtime.router.connection import Connection
from sage.utils.custom_logger import CustomLogger
import ray
from ray.actor import ActorHandle

from sage.utils.ray_init_helper import ensure_ray_initialized
if TYPE_CHECKING:
    from sage.core.api.base_environment import BaseEnvironment 
    from sage.jobmanager.execution_graph import ExecutionGraph, GraphNode
    from sage.runtime.runtime_context import RuntimeContext

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
        self.services: Dict[str, BaseServiceTask] = {}  # 存储服务实例
        self.is_running: bool = False
        self.logger.info(f"Dispatcher '{self.name}' construction complete")
        if env.platform == "remote":
            self.logger.info(f"Dispatcher '{self.name}' is running in remote mode")
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

    def receive_node_stop_signal(self, node_name: str) -> bool:
        """
        接收来自单个节点的停止信号并处理该节点
        
        Args:
            node_name: 要停止的节点名称
            
        Returns:
            bool: 如果所有节点都已停止返回True，否则返回False
        """
        self.logger.info(f"Dispatcher received node stop signal from: {node_name}")
        
        # 检查节点是否存在
        if node_name not in self.tasks:
            self.logger.warning(f"Node {node_name} not found in tasks")
            return False
        
        # 停止并清理指定节点
        try:
            task = self.tasks[node_name]
            task.stop()
            task.cleanup()
            
            # 从任务列表中移除
            del self.tasks[node_name]
            
            self.logger.info(f"Node {node_name} stopped and cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error stopping node {node_name}: {e}", exc_info=True)
            return False
        
        # 检查是否所有节点都已停止
        if len(self.tasks) == 0 and len(self.services) == 0:
            self.logger.info("All nodes and services stopped, dispatcher can be cleaned up")
            self.is_running = False
            return True
        else:
            self.logger.info(f"Remaining nodes: {len(self.tasks)}, services: {len(self.services)}")
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
        # 第三步：启动所有服务任务
        for service_name, service_task in self.services.items():
            try:
                if hasattr(service_task, 'start_running'):
                    service_task.start_running()
                elif hasattr(service_task, '_actor') and hasattr(service_task, 'start_running'):
                    # ActorWrapper包装的服务
                    import ray
                    ray.get(service_task.start_running.remote())
                self.logger.debug(f"Started service task: {service_name}")
            except Exception as e:
                self.logger.error(f"Failed to start service task {service_name}: {e}", exc_info=True)
        
        # 第四步：提交所有节点开始运行
        for node_name, task in self.tasks.items():
            try:
                task.start_running()
                self.logger.debug(f"Started node: {node_name}")
            except Exception as e:
                self.logger.error(f"Failed to start node {node_name}: {e}", exc_info=True)
        self.logger.info(f"Job submission completed: {len(self.tasks)} nodes, {len(self.services)} service tasks")
        self.is_running = True

    def _create_service_runtime_context(self, service_name: str) -> 'RuntimeContext':
        """
        为service task创建专用的runtime context
        从graph node的runtime context模板创建，但修改name为service name
        
        Args:
            service_name: 服务名称
            
        Returns:
            专用于该服务的runtime context
        """
        # 获取任意一个graph node的runtime context作为模板
        template_ctx = None
        for graph_node in self.graph.nodes.values():
            template_ctx = graph_node.ctx
            break
        
        if template_ctx is None:
            self.logger.warning(f"No graph nodes found to create template context for service {service_name}")
            return None
        
        # 手动创建新的RuntimeContext实例，只复制service task需要的关键字段
        # 由于RuntimeContext没有copy方法，我们需要手动创建一个新实例
        try:
            # 创建一个最小化的runtime context，只包含service task需要的字段
            service_ctx = type(template_ctx).__new__(type(template_ctx))
            
            # 复制基本字段但修改name
            service_ctx.name = service_name  # 修改为service name
            service_ctx.env_name = template_ctx.env_name
            service_ctx.env_base_dir = template_ctx.env_base_dir
            service_ctx.env_uuid = template_ctx.env_uuid
            service_ctx.env_console_log_level = template_ctx.env_console_log_level
            
            # 复制其他必要字段
            service_ctx.parallel_index = 0  # service不需要并行索引
            service_ctx.parallelism = 1     # service不需要并行度
            service_ctx.is_spout = False    # service不是spout
            service_ctx.delay = template_ctx.delay
            service_ctx.stop_signal_num = 0  # service不需要停止信号
            
            # 复制jobmanager信息
            service_ctx.jobmanager_host = template_ctx.jobmanager_host
            service_ctx.jobmanager_port = template_ctx.jobmanager_port
            
            # 初始化延迟属性
            service_ctx._logger = None
            service_ctx._stop_event = None
            service_ctx.received_stop_signals = None
            service_ctx.stop_signal_count = 0
            
            # 初始化服务相关属性
            service_ctx._service_manager = None
            service_ctx._service_names = None
            service_ctx._service_handles = {}
            service_ctx._wrapped_services = {}
            
            # 复制memory collection（如果存在）
            if hasattr(template_ctx, 'memory_collection'):
                service_ctx.memory_collection = template_ctx.memory_collection
            
            self.logger.debug(f"Created runtime context for service '{service_name}'")
            return service_ctx
            
        except Exception as e:
            self.logger.error(f"Failed to create runtime context for service {service_name}: {e}", exc_info=True)
            return None

    # Dispatcher will submit the job to LocalEngine or Ray Server.    
    def submit(self):
        """编译图结构，创建节点并建立连接"""
        self.logger.info(f"Compiling Job for graph: {self.name}")
        
        # 第零步：创建所有服务任务实例  
        for service_name, service_task_factory in self.env.service_task_factories.items():
            try:
                # 为service task创建专用的runtime context
                service_ctx = self._create_service_runtime_context(service_name)
                
                # 使用ServiceTaskFactory创建服务任务，注入runtime context
                service_task = service_task_factory.create_service_task(service_ctx)
                self.services[service_name] = service_task
                service_type = "Ray Actor (wrapped)" if service_task_factory.remote else "Local"
                self.logger.debug(f"Added {service_type} service task '{service_name}' of type '{service_task.__class__.__name__}' with runtime context")
            except Exception as e:
                self.logger.error(f"Failed to create service task {service_name}: {e}", exc_info=True)
                # 可以选择继续或停止，这里选择继续但记录错误

        # 第一步：创建所有节点实例
        for node_name, graph_node in self.graph.nodes.items():
            try:
                # task = graph_node.create_dag_node()
                task = graph_node.transformation.task_factory.create_task(graph_node.name, graph_node.ctx)

                self.tasks[node_name] = task

                self.logger.debug(f"Added node '{node_name}' of type '{task.__class__.__name__}'")
            except Exception as e:
                self.logger.error(f"Failed to create nodes: {e}", exc_info=True)
                raise e
        
        # 第二步：建立节点间的连接

        for node_name, graph_node in self.graph.nodes.items():
            try:
                self._setup_node_connections(node_name, graph_node)
            except Exception as e:
                self.logger.error(f"Error setting up connections for node {node_name}: {e}", exc_info=True)
                raise e
        
        try:
            self.start()
        except Exception as e:
            self.logger.error(f"Error starting dispatcher: {e}", exc_info=True)
            raise e

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

                # 判断目标任务类型：如果是ActorWrapper，则为ray类型，否则为local类型
                if hasattr(target_handle, '_actor'):
                    # 这是一个ActorWrapper，说明是Ray Actor
                    target_type = "ray"
                    # 对于Ray Actor，保持ActorWrapper包装以便透明调用
                    actual_target_handle = target_handle
                else:
                    # 这是一个本地任务
                    target_type = "local"
                    actual_target_handle = target_handle.get_object() if hasattr(target_handle, 'get_object') else target_handle

                connection = Connection(
                    broadcast_index=broadcast_index,
                    parallel_index=parallel_index,
                    target_name=target_name,
                    target_handle=actual_target_handle,
                    target_input_index=target_input_index,
                    target_type=target_type
                )
                try:
                    output_handle.add_connection(connection)
                    self.logger.debug(f"Setup connection: {node_name} -> {target_name} ({target_type})")
                    
                except Exception as e:
                    self.logger.error(f"Error setting up connection {node_name} -> {target_name}: {e}", exc_info=True)

    def stop(self):
        """停止所有任务和服务"""
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
        
        # 停止所有服务任务
        for service_name, service_task in self.services.items():
            try:
                if hasattr(service_task, 'stop'):
                    service_task.stop()
                elif hasattr(service_task, '_actor') and hasattr(service_task._actor, 'stop'):
                    # ActorWrapper包装的服务
                    service_task._actor.stop()
                self.logger.debug(f"Stopped service task: {service_name}")
            except Exception as e:
                self.logger.error(f"Error stopping service task {service_name}: {e}")
        
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
            # 停止所有任务和服务
            if self.is_running:
                self.stop()
            
            if self.remote:
                # 清理 Ray Actors
                self._cleanup_ray_actors()
                # 清理 Ray Services
                self._cleanup_ray_services()
            else:
                # 清理本地任务
                for node_name, task in self.tasks.items():
                    try:
                        task.cleanup()
                        self.logger.debug(f"Cleaned up task: {node_name}")
                    except Exception as e:
                        self.logger.error(f"Error cleaning up task {node_name}: {e}")
                
                # 清理本地服务任务
                for service_name, service_task in self.services.items():
                    try:
                        if hasattr(service_task, 'cleanup'):
                            service_task.cleanup()
                        self.logger.debug(f"Cleaned up service task: {service_name}")
                    except Exception as e:
                        self.logger.error(f"Error cleaning up service task {service_name}: {e}")
            
            # 清空任务和服务字典
            self.tasks.clear()
            self.services.clear()
            
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

    def _cleanup_ray_services(self):
        """清理所有Ray服务任务"""
        if not self.services:
            return

        self.logger.info(f"Cleaning up {len(self.services)} service tasks...")

        # 清理服务任务 - 现在统一使用相同的接口
        cleanup_results = []
        for service_name, service_task in self.services.items():
            try:
                if hasattr(service_task, 'cleanup_and_kill'):
                    # 这是一个ActorWrapper包装的Ray服务任务
                    cleanup_success, kill_success = service_task.cleanup_and_kill(
                        cleanup_timeout=5.0,
                        no_restart=True
                    )
                    cleanup_results.append((service_name, kill_success))
                    
                    if kill_success:
                        self.logger.debug(f"Successfully killed Ray service actor {service_name}")
                    else:
                        self.logger.warning(f"Failed to kill Ray service actor {service_name}")
                        
                elif hasattr(service_task, 'cleanup'):
                    # 这是一个本地服务任务
                    service_task.cleanup()
                    cleanup_results.append((service_name, True))
                    self.logger.debug(f"Successfully cleaned up local service task {service_name}")
                else:
                    self.logger.warning(f"Service task {service_name} does not support cleanup")
                    cleanup_results.append((service_name, False))
                        
            except Exception as e:
                self.logger.warning(f"Error during cleanup for service task {service_name}: {e}")
                cleanup_results.append((service_name, False))

        # 报告清理结果
        successful_cleanups = sum(1 for _, success in cleanup_results if success)
        
        if successful_cleanups == len(self.services):
            self.logger.info(f"Successfully cleaned up all {len(self.services)} service tasks")
        else:
            self.logger.warning(f"Service task cleanup completed: {successful_cleanups}/{len(self.services)} successful")

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

    def get_service_status(self) -> Dict[str, Any]:
        """获取所有服务任务的状态"""
        status = {}
        
        for service_name, service_task in self.services.items():
            try:
                if hasattr(service_task, 'get_statistics'):
                    service_status = service_task.get_statistics()
                elif hasattr(service_task, '_actor') and hasattr(service_task._actor, 'get_statistics'):
                    # ActorWrapper包装的服务
                    service_status = service_task._actor.get_statistics()
                else:
                    service_status = {
                        "service_name": service_name,
                        "type": service_task.__class__.__name__,
                        "status": "unknown"
                    }
                status[service_name] = service_status
            except Exception as e:
                status[service_name] = {
                    "service_name": service_name,
                    "error": str(e)
                }
        
        return status


    def get_statistics(self) -> Dict[str, Any]:
        """获取dispatcher统计信息"""
        return {
            "name": self.name,
            "is_running": self.is_running,
            "task_count": len(self.tasks),
            "service_count": len(self.services),
            "task_status": self.get_task_status(),
            "service_status": self.get_service_status()
        }