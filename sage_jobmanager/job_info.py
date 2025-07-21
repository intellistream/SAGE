import time
from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING
import threading

if TYPE_CHECKING:
    from sage_core.environment.base_environment import BaseEnvironment
    from sage_jobmanager.execution_graph import ExecutionGraph
    from sage_runtime.dispatcher import Dispatcher


class JobInfo:
    """封装Job的完整信息和状态管理"""
    
    def __init__(self, 
                 env: 'BaseEnvironment',
                 graph: 'ExecutionGraph', 
                 dispatcher: 'Dispatcher',
                 uuid: str):
        self.env = env
        self.graph = graph
        self.dispatcher = dispatcher
        self.uuid = uuid
        
        # 状态管理
        self._status = "submitted"
        self._created_at = time.time()
        self._started_at: Optional[float] = None
        self._stopped_at: Optional[float] = None
        self._error: Optional[str] = None
        
        # 统计信息
        self._processed_count = 0
        self._error_count = 0
        self._last_update_time = time.time()
        
        # 线程锁
        self._lock = threading.RLock()
    
    @property
    def status(self) -> str:
        """获取当前状态"""
        with self._lock:
            return self._status
    
    def update_status(self, new_status: str, error: Optional[str] = None):
        """更新状态"""
        with self._lock:
            self._status = new_status
            self._last_update_time = time.time()
            
            if new_status == "running" and self._started_at is None:
                self._started_at = time.time()
            elif new_status in ["stopped", "failed", "completed"]:
                if self._stopped_at is None:
                    self._stopped_at = time.time()
            
            if error:
                self._error = error
                self._error_count += 1
    
    def increment_processed(self, count: int = 1):
        """增加处理计数"""
        with self._lock:
            self._processed_count += count
            self._last_update_time = time.time()
    
    def increment_errors(self, count: int = 1):
        """增加错误计数"""
        with self._lock:
            self._error_count += count
            self._last_update_time = time.time()
    
    def get_runtime_seconds(self) -> Optional[float]:
        """获取运行时长（秒）"""
        with self._lock:
            if self._started_at is None:
                return None
            
            end_time = self._stopped_at or time.time()
            return end_time - self._started_at
    
    def get_status(self) -> Dict[str, Any]:
        """返回可序列化的状态字典，用于监控"""
        with self._lock:
            # 基础信息
            status_dict = {
                "uuid": self.uuid,
                "env_name": self.env.name,
                "status": self._status,
                
                # 时间信息
                "created_at": self._created_at,
                "created_at_str": datetime.fromtimestamp(self._created_at).isoformat(),
                "started_at": self._started_at,
                "stopped_at": self._stopped_at,
                "last_update_time": self._last_update_time,
                "last_update_str": datetime.fromtimestamp(self._last_update_time).isoformat(),
                
                # 运行时长
                "runtime_seconds": self.get_runtime_seconds(),
                
                # 统计信息
                "processed_count": self._processed_count,
                "error_count": self._error_count,
                
                # 图信息
                "nodes_count": len(self.graph.nodes),
                "edges_count": len(self.graph.edges),
                
                # 错误信息
                "last_error": self._error
            }
            
            # 运行时长的格式化字符串
            if status_dict["runtime_seconds"] is not None:
                seconds = int(status_dict["runtime_seconds"])
                hours, remainder = divmod(seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                status_dict["runtime_str"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                status_dict["runtime_str"] = None
            
            # 尝试获取Dispatcher的详细状态
            try:
                dispatcher_status = self.dispatcher.get_status()
                status_dict["dispatcher"] = dispatcher_status
            except Exception as e:
                status_dict["dispatcher"] = {"error": f"Failed to get dispatcher status: {e}"}
            
            # 尝试获取环境类型信息
            try:
                status_dict["env_type"] = self.env.__class__.__name__
                status_dict["env_mode"] = getattr(self.env, 'mode', 'unknown')
            except Exception:
                status_dict["env_type"] = "unknown"
                status_dict["env_mode"] = "unknown"
            
            return status_dict
    
    def get_summary(self) -> Dict[str, Any]:
        """返回简化的状态摘要"""
        with self._lock:
            return {
                "uuid": self.uuid,
                "env_name": self.env.name,
                "status": self._status,
                "runtime_seconds": self.get_runtime_seconds(),
                "processed_count": self._processed_count,
                "error_count": self._error_count,
                "nodes_count": len(self.graph.nodes)
            }
    
    def __repr__(self) -> str:
        return f"JobInfo(uuid={self.uuid[:8]}..., env={self.env.name}, status={self._status})"