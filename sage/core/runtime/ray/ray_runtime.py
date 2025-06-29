from typing import Dict, List, Optional, Any, Union
from sage.core.runtime.ray.ray_dag_node import RayDAGNode
import logging, ray, time, threading 
from sage.core.runtime.base_runtime import BaseRuntime
from sage.utils.custom_logger import CustomLogger
from ray.actor import ActorHandle

class RayRuntime(BaseRuntime):
    """
    Ray 执行后端，支持单个Ray节点和完整Ray DAG的管理
    """
    _instance = None
    _lock = threading.Lock()


    def __init__(self, monitoring_interval: float = 1.0):
        """
        Initialize Ray execution backend.
        
        Args:
            monitoring_interval: Interval in seconds for monitoring status
            session_folder: Session folder for logging
        """
        # 确保Ray已初始化
        if not ray.is_initialized():
            ray.init()
            
        self.name = "RayRuntime"
        self.session_folder = CustomLogger.get_session_folder()
        
        # Ray DAG 管理（保留向后兼容）
        self.running_dags: Dict[str, RayDAG] = {}  # handle -> RayDAG映射
        self.dag_spout_futures: Dict[str, List[ray.ObjectRef]] = {}  # handle -> spout futures
        self.dag_metadata: Dict[str, Dict[str, Any]] = {}  # handle -> metadata
        
        # Ray节点管理
        self.running_nodes: Dict[str, ActorHandle] = {}  # node_name -> ActorHandle
        self.node_metadata: Dict[str, Dict[str, Any]] = {}  # node_name -> metadata
        self.node_handles: Dict[str, str] = {}  # handle -> node_name
        self.handle_to_node: Dict[str, str] = {}  # handle -> node_name
        self.node_spout_futures: Dict[str, ray.ObjectRef] = {}  # node_name -> spout future
        
        self.next_handle_id = 0
        self.monitoring_interval = monitoring_interval
        
        self.logger = CustomLogger(
            object_name=f"RayRuntime",
            log_level="DEBUG",
            console_output=False,
            file_output=True
        )
    def __new__(cls, monitoring_interval: float = 1.0):
        # 禁止直接实例化
        raise RuntimeError("请通过 get_instance() 方法获取实例")
    
    @classmethod
    def get_instance(cls, monitoring_interval: float = 1.0):
        """获取RayRuntime的唯一实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    # 绕过 __new__ 的异常，直接创建实例
                    instance = super().__new__(cls)
                    instance.__init__(monitoring_interval)
                    cls._instance = instance
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置实例（主要用于测试）"""
        with cls._lock:
            if cls._instance:
                cls._instance.shutdown()
                cls._instance = None
    # ==================== Ray节点管理接口 ====================
    
    def submit_node(self, node_class, node_name: str, operator_class, 
                   operator_config: Dict = None, is_spout: bool = False) -> str:
        """
        提交单个Ray节点到运行时
        
        Args:
            node_class: Ray节点类（通常是RayMultiplexerDagNode）
            node_name: 节点名称
            operator_class: 操作符类
            operator_config: 操作符配置
            is_spout: 是否为spout节点
            
        Returns:
            str: 节点句柄
        """
        if node_name in self.running_nodes:
            raise ValueError(f"Node '{node_name}' already exists")
        
        self.logger.info(f"Submitting Ray node '{node_name}' to {self.name}")
        
        try:
            # 创建Ray Actor
            actor_handle = node_class.remote(
                name=node_name,
                function_class=operator_class,
                operator_config=operator_config or {},
                is_spout=is_spout,
                session_folder=self.session_folder
            )
            
            # 生成handle
            handle = f"ray_node_{self.next_handle_id}"
            self.next_handle_id += 1
            
            # 存储节点信息
            self.running_nodes[node_name] = actor_handle
            self.node_metadata[node_name] = {
                'is_spout': is_spout,
                'operator_class': operator_class.__name__,
                'start_time': time.time(),
                'status': 'created'
            }
            self.node_handles[handle] = node_name
            self.handle_to_node[handle] = node_name
            
            self.logger.info(f"Ray node '{node_name}' created successfully with handle: {handle}")
            return handle
            
        except Exception as e:
            self.logger.error(f"Failed to create Ray node '{node_name}': {e}")
            raise
    
    def submit_actor_instance(self, node_instance: ActorHandle, node_name: str) -> str:
        """
        提交已创建的Ray节点实例
        
        Args:
            node_instance: Ray Actor实例
            node_name: 节点名称
            
        Returns:
            str: 节点句柄
        """
        if node_name in self.running_nodes:
            raise ValueError(f"Node '{node_name}' already exists")
        
        # 生成handle
        handle = f"ray_node_{self.next_handle_id}"
        self.next_handle_id += 1
        
        # 存储节点信息
        self.running_nodes[node_name] = node_instance
        self.node_metadata[node_name] = {
            'start_time': time.time(),
            'status': 'submitted'
        }
        self.node_handles[handle] = node_name
        self.handle_to_node[handle] = node_name
        
        self.logger.info(f"Ray node instance '{node_name}' submitted with handle: {handle}")
        return handle
    
    def submit_actors(self, nodes: List[ActorHandle], node_names: List[str]) -> List[str]:
        """
        批量提交Ray节点实例
        
        Args:
            nodes: Ray Actor实例列表
            node_names: 节点名称列表
            
        Returns:
            List[str]: 节点句柄列表
        """
        if len(nodes) != len(node_names):
            raise ValueError("nodes and node_names must have the same length")
        
        handles = []
        for actor_instance, node_name in zip(nodes, node_names):
            try:
                handle = self.submit_actor_instance(actor_instance, node_name)
                handles.append(handle)
                self.start_node(handle)  # 自动启动节点
            except Exception as e:
                self.logger.error(f"Failed to submit node '{node_name}': {e}")
                # 停止已经提交的节点
                for h in handles:
                    self.stop_node(h)
                raise
        
        self.logger.info(f"Successfully submitted {len(handles)} Ray nodes")
        return handles
    
    def start_node(self, node_handle: str):
        """
        启动Ray节点
        
        Args:
            node_handle: 节点句柄
        """
        if node_handle not in self.handle_to_node:
            raise ValueError(f"Node handle '{node_handle}' not found")
        
        node_name = self.handle_to_node[node_handle]
        actor_handle = self.running_nodes[node_name]
        
        try:
            # 检查是否为spout节点
            is_spout = self.node_metadata[node_name].get('is_spout', False)
            
            if is_spout:
                # Spout节点启动数据生成循环
                future = actor_handle.start.remote()
                self.node_spout_futures[node_name] = future
                self.logger.info(f"Started Ray spout node '{node_name}'")
            else:
                # 非Spout节点启动就绪状态
                future = actor_handle.start.remote()
                self.logger.info(f"Started Ray node '{node_name}' in ready state")
            
            # 更新状态
            self.node_metadata[node_name]['status'] = 'running'
            
        except Exception as e:
            self.logger.error(f"Failed to start Ray node '{node_name}': {e}")
            raise
    
    def start_all_nodes(self):
        """启动所有节点"""
        self.logger.info("Starting all Ray nodes...")
        
        spout_count = 0
        ready_count = 0
        
        for handle in self.handle_to_node.keys():
            try:
                node_name = self.handle_to_node[handle]
                is_spout = self.node_metadata[node_name].get('is_spout', False)
                
                self.start_node(handle)
                
                if is_spout:
                    spout_count += 1
                else:
                    ready_count += 1
                    
            except Exception as e:
                self.logger.error(f"Failed to start node with handle {handle}: {e}")
        
        self.logger.info(f"Started {spout_count} spout nodes and {ready_count} ready nodes")
    
    def stop_node(self, node_handle: str):
        """
        停止Ray节点
        
        Args:
            node_handle: 节点句柄
        """
        if node_handle not in self.handle_to_node:
            self.logger.warning(f"Node handle '{node_handle}' not found")
            return
        
        node_name = self.handle_to_node[node_handle]
        actor_handle = self.running_nodes[node_name]
        
        try:
            # 停止Actor
            actor_handle.stop.remote()
            
            # 清理spout future
            self.node_spout_futures.pop(node_name, None)
            
            # 更新状态
            self.node_metadata[node_name]['status'] = 'stopped'
            self.node_metadata[node_name]['end_time'] = time.time()
            
            self.logger.info(f"Ray node '{node_name}' stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping Ray node '{node_name}': {e}")
    
    def stop_all_nodes(self):
        """停止所有节点"""
        self.logger.info("Stopping all Ray nodes...")
        
        handles_to_stop = list(self.handle_to_node.keys())
        for handle in handles_to_stop:
            self.stop_node(handle)
        
        self.logger.info(f"Stopped {len(handles_to_stop)} Ray nodes")
    
    def remove_node(self, node_handle: str):
        """
        移除Ray节点并清理资源
        
        Args:
            node_handle: 节点句柄
        """
        if node_handle not in self.handle_to_node:
            self.logger.warning(f"Node handle '{node_handle}' not found")
            return
        
        node_name = self.handle_to_node[node_handle]
        actor_handle = self.running_nodes[node_name]
        
        try:
            # 停止并杀死Actor
            self.stop_node(node_handle)
            ray.kill(actor_handle)
            
            # 清理映射关系
            self.running_nodes.pop(node_name, None)
            self.node_metadata.pop(node_name, None)
            self.node_handles.pop(node_handle, None)
            self.handle_to_node.pop(node_handle, None)
            self.node_spout_futures.pop(node_name, None)
            
            self.logger.info(f"Ray node '{node_name}' removed")
            
        except Exception as e:
            self.logger.error(f"Error removing Ray node '{node_name}': {e}")
    
    def get_node_status(self, node_handle: str) -> Dict[str, Any]:
        """
        获取Ray节点状态
        
        Args:
            node_handle: 节点句柄
            
        Returns:
            Dict: 节点状态信息
        """
        if node_handle not in self.handle_to_node:
            return {"status": "not_found"}
        
        node_name = self.handle_to_node[node_handle]
        actor_handle = self.running_nodes[node_name]
        metadata = self.node_metadata[node_name]
        
        try:
            # 非阻塞健康检查
            health_future = actor_handle.health_check.remote()
            ready, not_ready = ray.wait([health_future], timeout=0.1)
            
            if ready:
                health_info = ray.get(ready[0])
            else:
                health_info = {"status": "busy"}
                
        except Exception as e:
            health_info = {"status": "error", "error": str(e)}
        
        status_info = {
            "handle": node_handle,
            "node_name": node_name,
            "backend": "ray_node",
            "status": metadata.get('status', 'unknown'),
            "is_spout": metadata.get('is_spout', False),
            "operator_class": metadata.get('operator_class', 'unknown'),
            "start_time": metadata.get('start_time'),
            "health": health_info
        }
        
        # 计算运行时间
        if 'start_time' in metadata:
            if 'end_time' in metadata:
                status_info['duration'] = metadata['end_time'] - metadata['start_time']
            else:
                status_info['duration'] = time.time() - metadata['start_time']
        
        return status_info
    
    def get_running_nodes(self) -> List[str]:
        """获取所有运行中的节点名称"""
        return list(self.running_nodes.keys())
    
    def get_node_by_name(self, node_name: str) -> Optional[ActorHandle]:
        """根据名称获取节点"""
        return self.running_nodes.get(node_name)
    
    def wait_for_node_completion(self, node_handle: str, timeout: Optional[float] = None) -> bool:
        """
        等待spout节点完成执行
        
        Args:
            node_handle: 节点句柄
            timeout: 超时时间（秒），None表示无限等待
            
        Returns:
            是否成功完成
        """
        if node_handle not in self.handle_to_node:
            return False
        
        node_name = self.handle_to_node[node_handle]
        
        if node_name not in self.node_spout_futures:
            return True  # 不是spout节点或没有运行的future
        
        spout_future = self.node_spout_futures[node_name]
        
        try:
            ray.get(spout_future, timeout=timeout)
            self.logger.info(f"Ray node '{node_name}' completed successfully")
            
            # 更新状态
            self.node_metadata[node_name]['status'] = 'completed'
            self.node_metadata[node_name]['end_time'] = time.time()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ray node '{node_name}' failed or timed out: {e}")
            return False
    
    # ==================== Ray DAG管理接口（向后兼容） ====================
    
    # def submit_task(self, ray_dag: RayDAG) -> str:
    #     """
    #     提交 Ray DAG 执行任务（向后兼容接口）
        
    #     Args:
    #         ray_dag: RayDAG 实例
    #     """
    #     if not isinstance(ray_dag, RayDAG):
    #         raise TypeError("Task must be RayDAG instance")
        
    #     if not ray_dag.is_valid():
    #         raise ValueError("Invalid RayDAG: missing spouts or broken dependencies")
        
    #     handle = f"ray_dag_{self.next_handle_id}"
    #     self.next_handle_id += 1
        
    #     self.logger.info(f"Submitting Ray DAG {ray_dag.name} with handle {handle}")
        
    #     try:
    #         # 启动 DAG 执行
    #         spout_futures = self._start_dag(ray_dag)
            
    #         # 存储DAG信息
    #         self.running_dags[handle] = ray_dag
    #         self.dag_spout_futures[handle] = spout_futures
    #         self.dag_metadata[handle] = {
    #             'actor_count': ray_dag.get_actor_count(),
    #             'start_time': time.time(),
    #             'status': 'running'
    #         }
            
    #         self.logger.info(f"Ray DAG {handle} started successfully with {len(spout_futures)} spout actors")
    #         return handle
            
    #     except Exception as e:
    #         self.logger.error(f"Failed to start Ray DAG {ray_dag.name}: {e}", exc_info=True)
    #         raise
    
    # def _start_dag(self, ray_dag: RayDAG) -> List[ray.ObjectRef]:
    #     """启动DAG中的所有spout actors"""
    #     spout_actors = ray_dag.get_spout_actors()
        
    #     if not spout_actors:
    #         raise RuntimeError("No spout actors found in DAG")
        
    #     spout_futures = []
    #     for spout_actor in spout_actors:
    #         try:
    #             future = spout_actor.start.remote()
    #             spout_futures.append(future)
    #             self.logger.debug(f"Started spout actor in DAG {ray_dag.name}")
    #         except Exception as e:
    #             self.logger.error(f"Failed to start spout actor in DAG {ray_dag.name}: {e}")
    #             raise
        
    #     return spout_futures
    
    # def stop_task(self, task_handle: str):
    #     """停止 Ray DAG 执行（向后兼容接口）"""
    #     if task_handle not in self.running_dags:
    #         self.logger.warning(f"DAG handle {task_handle} not found")
    #         return
        
    #     ray_dag = self.running_dags[task_handle]
    #     self.logger.info(f"Stopping Ray DAG {task_handle}")
        
    #     try:
    #         # 停止所有actors
    #         self._stop_all_actors(ray_dag)
            
    #         # 更新状态
    #         if task_handle in self.dag_metadata:
    #             self.dag_metadata[task_handle]['status'] = 'stopped'
    #             self.dag_metadata[task_handle]['end_time'] = time.time()
            
    #         self.logger.info(f"Ray DAG {task_handle} stopped successfully")
            
    #     except Exception as e:
    #         self.logger.error(f"Error stopping Ray DAG {task_handle}: {e}", exc_info=True)
        
    #     finally:
    #         # 清理资源
    #         self._cleanup_dag(task_handle)
    
    # def _stop_all_actors(self, ray_dag: RayDAG):
    #     """停止 DAG 中的所有 actors"""
    #     stop_futures = []
    #     for name, actor in ray_dag.get_all_actors().items():
    #         try:
    #             future = actor.stop.remote()
    #             stop_futures.append(future)
    #         except Exception as e:
    #             self.logger.warning(f"Failed to stop actor {name}: {e}")
        
    #     # 等待所有actors停止
    #     if stop_futures:
    #         try:
    #             ray.get(stop_futures, timeout=30)  # 30秒超时
    #             self.logger.debug("All actors stopped successfully")
    #         except Exception as e:
    #             self.logger.error(f"Some actors failed to stop gracefully: {e}")
    
    # def _cleanup_dag(self, task_handle: str):
    #     """清理 DAG 资源"""
    #     if task_handle in self.running_dags:
    #         ray_dag = self.running_dags[task_handle]
            
    #         # 杀死所有actors
    #         for name, actor in ray_dag.get_all_actors().items():
    #             try:
    #                 ray.kill(actor)
    #                 self.logger.debug(f"Killed actor: {name}")
    #             except Exception as e:
    #                 self.logger.warning(f"Failed to kill actor {name}: {e}")
        
    #     # 清理映射关系
    #     self.running_dags.pop(task_handle, None)
    #     self.dag_spout_futures.pop(task_handle, None)
    #     self.dag_metadata.pop(task_handle, None)
    
    # def get_status(self, task_handle: str) -> Dict[str, Any]:
    #     """获取 Ray DAG 状态（向后兼容接口）"""
    #     if task_handle not in self.running_dags:
    #         return {"status": "not_found"}
        
    #     metadata = self.dag_metadata.get(task_handle, {})
    #     ray_dag = self.running_dags[task_handle]
    #     spout_futures = self.dag_spout_futures.get(task_handle, [])
        
    #     # 检查spout actors状态
    #     completed_spouts = 0
    #     if spout_futures:
    #         ready, not_ready = ray.wait(spout_futures, timeout=0.1)
    #         completed_spouts = len(ready)
        
    #     # 检查actor健康状态
    #     actor_health = self._check_actor_health(ray_dag)
        
    #     status_info = {
    #         "status": metadata.get('status', 'unknown'),
    #         "backend": "ray_dag",
    #         "dag_id": ray_dag.name,
    #         "actor_count": metadata.get('actor_count', 0),
    #         "spout_count": len(spout_futures),
    #         "completed_spouts": completed_spouts,
    #         "actor_health": actor_health,
    #         "start_time": metadata.get('start_time'),
    #         "connections": len(ray_dag.get_connections())
    #     }
        
    #     # 计算运行时间
    #     if 'start_time' in metadata:
    #         if 'end_time' in metadata:
    #             status_info['duration'] = metadata['end_time'] - metadata['start_time']
    #         else:
    #             status_info['duration'] = time.time() - metadata['start_time']
        
    #     return status_info
    
    # def _check_actor_health(self, ray_dag: RayDAG) -> Dict[str, str]:
    #     """检查 actors 健康状态"""
    #     actor_health = {}
        
    #     for name, actor in ray_dag.get_all_actors().items():
    #         try:
    #             # 非阻塞健康检查
    #             ready, not_ready = ray.wait([actor.is_running.remote()], timeout=0.1)
    #             if ready:
    #                 is_running = ray.get(ready[0])
    #                 actor_health[name] = "running" if is_running else "stopped"
    #             else:
    #                 actor_health[name] = "busy"  # Actor正在处理其他请求
                    
    #         except Exception as e:
    #             actor_health[name] = f"error: {str(e)}"
        
    #     return actor_health
    
    def wait_for_completion(self, task_handle: str, timeout: Optional[float] = None) -> bool:
        """等待 DAG 完成执行（向后兼容接口）"""
        if task_handle not in self.running_dags:
            return False
        
        spout_futures = self.dag_spout_futures.get(task_handle, [])
        if not spout_futures:
            return True  # 没有spout futures，认为已完成
        
        try:
            ray.get(spout_futures, timeout=timeout)
            self.logger.info(f"DAG {task_handle} completed successfully")
            
            # 更新状态
            if task_handle in self.dag_metadata:
                self.dag_metadata[task_handle]['status'] = 'completed'
                self.dag_metadata[task_handle]['end_time'] = time.time()
            
            return True
            
        except Exception as e:
            self.logger.error(f"DAG {task_handle} failed or timed out: {e}")
            return False
    
    # ==================== 通用管理接口 ====================
    
    def get_runtime_info(self) -> Dict[str, Any]:
        """获取运行时信息"""
        return {
            "name": self.name,
            "running_nodes_count": len(self.running_nodes),
            "running_nodes": list(self.running_nodes.keys()),
            "running_dags_count": len(self.running_dags),
            "running_dags": list(self.running_dags.keys()),
            "ray_initialized": ray.is_initialized()
        }
    
    def shutdown(self):
        """关闭运行时和所有资源"""
        self.logger.info("Shutting down RayRuntime...")
        
        # 停止所有节点
        self.stop_all_nodes()
        
        # 停止所有DAG
        for handle in list(self.running_dags.keys()):
            self.stop_task(handle)
        
        self.logger.info("RayRuntime shutdown completed")
    
    def __del__(self):
        self.logger.info("calling del")

        """析构函数，确保资源清理"""
        try:
            self.shutdown()
        except:
            pass