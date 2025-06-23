from typing import Dict, List, Optional, Any
# from sage.archive.raydag_task import RayDAGTask
from sage.core.dag.ray.ray_dag import RayDAG
import logging, ray, time
from sage.core.runtime.base_runtime import BaseRuntime



class RayRuntime(BaseRuntime):
    """Ray DAG 专用执行后端"""
    
    def __init__(self, monitoring_interval: float = 1.0):
        """
        Initialize Ray DAG execution backend.
        
        Args:
            monitoring_interval: Interval in seconds for monitoring DAG status
        """
        # 确保Ray已初始化
        if not ray.is_initialized():
            ray.init(temp_dir="./ray_tmp")
        self.name = "RayRuntime"
        self.running_dags: Dict[str, RayDAG] = {}  # handle -> RayDAG映射
        self.dag_spout_futures: Dict[str, List[ray.ObjectRef]] = {}  # handle -> spout futures
        self.dag_metadata: Dict[str, Dict[str, Any]] = {}  # handle -> metadata
        self.next_handle_id = 0
        self.monitoring_interval = monitoring_interval
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def submit_task(self, ray_dag:RayDAG) -> str:
        """
        提交 Ray DAG 执行任务
        
        Args:
            ray_dag: 应该是 RayDAG 实例或包含 RayDAG 的任务包装器
        """
        if not isinstance(ray_dag, RayDAG):
            raise TypeError("Task must be RayDAG instance")
        
        if not ray_dag.is_valid():
            raise ValueError("Invalid RayDAG: missing spouts or broken dependencies")
        
        handle = f"ray_dag_{self.next_handle_id}"
        self.next_handle_id += 1
        
        self.logger.info(f"Submitting Ray DAG {ray_dag.name} with handle {handle}")
        
        try:
            # 启动 DAG 执行
            if ray_dag.strategy == "streaming":
                spout_futures = self._start_streaming_dag(ray_dag)
            elif ray_dag.strategy == "oneshot":
                spout_futures = self._start_oneshot_dag(ray_dag)
            else:
                raise ValueError(f"Unsupported DAG strategy: {ray_dag.strategy}")
            
            # 存储DAG信息
            self.running_dags[handle] = ray_dag
            self.dag_spout_futures[handle] = spout_futures
            self.dag_metadata[handle] = {
                'strategy': ray_dag.strategy,
                'actor_count': ray_dag.get_actor_count(),
                'start_time': time.time(),
                'status': 'running'
            }
            
            self.logger.info(f"Ray DAG {handle} started successfully with {len(spout_futures)} spout actors")
            return handle
            
        except Exception as e:
            self.logger.error(f"Failed to start Ray DAG {ray_dag.name}: {e}", exc_info=True)
            raise
    
    def _start_streaming_dag(self, ray_dag: RayDAG) -> List[ray.ObjectRef]:
        """启动流式 DAG"""
        spout_actors = ray_dag.get_spout_actors()
        
        if not spout_actors:
            raise RuntimeError("No spout actors found in streaming DAG")
        
        spout_futures = []
        for spout_actor in spout_actors:
            try:
                self.logger.debug(f"Started streaming spout actor in DAG {ray_dag.name}")
                future = spout_actor.start_spout.remote()
                spout_futures.append(future)
            except Exception as e:
                self.logger.error(f"Failed to start spout actor in DAG {ray_dag.name}: {e}")
                raise
        
        return spout_futures
    
    def _start_oneshot_dag(self, ray_dag: RayDAG) -> List[ray.ObjectRef]:
        """启动一次性 DAG"""
        spout_actors = ray_dag.get_spout_actors()
        
        if not spout_actors:
            raise RuntimeError("No spout actors found in oneshot DAG")
        
        spout_futures = []
        for spout_actor in spout_actors:
            try:
                future = spout_actor.start_spout.remote()
                spout_futures.append(future)
                self.logger.debug(f"Started oneshot spout actor in DAG {ray_dag.name}")
            except Exception as e:
                self.logger.error(f"Failed to start spout actor in DAG {ray_dag.name}: {e}")
                raise
        
        return spout_futures
    
    def stop_task(self, task_handle: str):
        """停止 Ray DAG 执行"""
        if task_handle not in self.running_dags:
            self.logger.warning(f"DAG handle {task_handle} not found")
            return
        
        ray_dag = self.running_dags[task_handle]
        self.logger.info(f"Stopping Ray DAG {task_handle}")
        
        try:
            # 停止所有actors
            self._stop_all_actors(ray_dag)
            
            # 更新状态
            if task_handle in self.dag_metadata:
                self.dag_metadata[task_handle]['status'] = 'stopped'
                self.dag_metadata[task_handle]['end_time'] = time.time()
            
            self.logger.info(f"Ray DAG {task_handle} stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping Ray DAG {task_handle}: {e}", exc_info=True)
        
        finally:
            # 清理资源
            self._cleanup_dag(task_handle)
    
    def _stop_all_actors(self, ray_dag: RayDAG):
        """停止 DAG 中的所有 actors"""
        stop_futures = []
        for name, actor in ray_dag.get_all_actors().items():
            try:
                future = actor.stop.remote()
                stop_futures.append(future)
            except Exception as e:
                self.logger.warning(f"Failed to stop actor {name}: {e}")
        
        # 等待所有actors停止
        if stop_futures:
            try:
                ray.get(stop_futures, timeout=30)  # 30秒超时
                self.logger.debug("All actors stopped successfully")
            except Exception as e:
                self.logger.error(f"Some actors failed to stop gracefully: {e}")
    
    def _cleanup_dag(self, task_handle: str):
        """清理 DAG 资源"""
        if task_handle in self.running_dags:
            ray_dag = self.running_dags[task_handle]
            
            # 杀死所有actors
            for name, actor in ray_dag.get_all_actors().items():
                try:
                    ray.kill(actor)
                    self.logger.debug(f"Killed actor: {name}")
                except Exception as e:
                    self.logger.warning(f"Failed to kill actor {name}: {e}")
        
        # 清理映射关系
        self.running_dags.pop(task_handle, None)
        self.dag_spout_futures.pop(task_handle, None)
        self.dag_metadata.pop(task_handle, None)
    
    def get_status(self, task_handle: str) -> Dict[str, Any]:
        """获取 Ray DAG 状态"""
        if task_handle not in self.running_dags:
            return {"status": "not_found"}
        
        metadata = self.dag_metadata.get(task_handle, {})
        ray_dag = self.running_dags[task_handle]
        spout_futures = self.dag_spout_futures.get(task_handle, [])
        
        # 检查spout actors状态
        completed_spouts = 0
        if spout_futures:
            ready, not_ready = ray.wait(spout_futures, timeout=0.1)
            completed_spouts = len(ready)
        
        # 检查actor健康状态
        actor_health = self._check_actor_health(ray_dag)
        
        status_info = {
            "status": metadata.get('status', 'unknown'),
            "backend": "ray_dag",
            "dag_id": ray_dag.name,
            "strategy": metadata.get('strategy', 'unknown'),
            "actor_count": metadata.get('actor_count', 0),
            "spout_count": len(spout_futures),
            "completed_spouts": completed_spouts,
            "actor_health": actor_health,
            "start_time": metadata.get('start_time'),
            "connections": len(ray_dag.get_connections())
        }
        
        # 计算运行时间
        if 'start_time' in metadata:
            if 'end_time' in metadata:
                status_info['duration'] = metadata['end_time'] - metadata['start_time']
            else:
                status_info['duration'] = time.time() - metadata['start_time']
        
        return status_info
    
    def _check_actor_health(self, ray_dag: RayDAG) -> Dict[str, str]:
        """检查 actors 健康状态"""
        actor_health = {}
        
        for name, actor in ray_dag.get_all_actors().items():
            try:
                # 非阻塞健康检查
                ready, not_ready = ray.wait([actor.is_running.remote()], timeout=0.1)
                if ready:
                    is_running = ray.get(ready[0])
                    actor_health[name] = "running" if is_running else "stopped"
                else:
                    actor_health[name] = "busy"  # Actor正在处理其他请求
                    
            except Exception as e:
                actor_health[name] = f"error: {str(e)}"
        
        return actor_health
    
    def wait_for_completion(self, task_handle: str, timeout: Optional[float] = None) -> bool:
        """
        等待 DAG 完成执行（主要用于 oneshot 策略）
        
        Args:
            task_handle: DAG 句柄
            timeout: 超时时间（秒），None表示无限等待
            
        Returns:
            是否成功完成
        """
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
    
    def list_running_dags(self) -> List[str]:
        """列出所有正在运行的 DAG 句柄"""
        return list(self.running_dags.keys())
    
    def get_dag_info(self, task_handle: str) -> Optional[Dict[str, Any]]:
        """获取 DAG 详细信息"""
        if task_handle not in self.running_dags:
            return None
        
        ray_dag = self.running_dags[task_handle]
        return {
            'handle': task_handle,
            'dag_id': ray_dag.name,
            'strategy': ray_dag.strategy,
            'actor_count': ray_dag.get_actor_count(),
            'connections': ray_dag.get_connections(),
            'spout_actors': ray_dag.spout_actors,
            'metadata': self.dag_metadata.get(task_handle, {})
        }
