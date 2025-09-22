from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING
import time

if TYPE_CHECKING:
    from sage.core.api.base_environment import BaseEnvironment
    from sage.kernel.jobmanager.compiler import ExecutionGraph
    from sage.kernel.runtime.dispatcher import Dispatcher

class JobInfo:
    """作业信息类，用于跟踪和管理单个作业的状态"""
    
    def __init__(self, environment: 'BaseEnvironment', graph: 'ExecutionGraph', 
                 dispatcher: 'Dispatcher', uuid: str):
        self.environment = environment
        self.graph = graph
        self.dispatcher = dispatcher
        self.uuid = uuid
        
        # 状态信息
        self.status = "initializing"  # initializing, running, stopped, failed, restarting
        self.start_time = datetime.now()
        self.stop_time: Optional[datetime] = None
        self.last_update_time = datetime.now()
        self.error_message: Optional[str] = None
        
        # 统计信息
        self.restart_count = 0
        
        # 元数据信息
        self.metadata: Dict[str, Any] = {}
        
    def add_metadata(self, key: str, value: Any):
        """添加元数据"""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """获取元数据"""
        return self.metadata.get(key, default)
        
    def update_status(self, new_status: str, error: Optional[str] = None):
        """更新作业状态"""
        old_status = self.status
        self.status = new_status
        self.last_update_time = datetime.now()
        
        if error:
            self.error_message = error
        
        if new_status in ["stopped", "failed"]:
            self.stop_time = datetime.now()
        elif new_status == "running" and old_status in ["stopped", "failed", "restarting"]:
            # 重新开始运行，重置停止时间
            self.stop_time = None
    
    def get_runtime(self) -> str:
        """获取运行时间字符串"""
        if self.stop_time:
            runtime = self.stop_time - self.start_time
        else:
            runtime = datetime.now() - self.start_time
        
        total_seconds = int(runtime.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def get_summary(self) -> Dict[str, Any]:
        """获取作业摘要信息"""
        return {
            "uuid": self.uuid,
            "name": self.environment.name,
            "status": self.status,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "runtime": self.get_runtime(),
            "restart_count": self.restart_count,
            "last_update": self.last_update_time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def get_status(self) -> Dict[str, Any]:
        """获取详细状态信息"""
        status_info = self.get_summary()
        
        # 添加详细信息
        status_info.update({
            "environment": {
                "name": self.environment.name,
                "platform": getattr(self.environment, 'platform', 'unknown'),
                "description": getattr(self.environment, 'description', '')
            },
            "dispatcher": {
                "task_count": len(self.dispatcher.tasks),
                "is_running": self.dispatcher.is_running
            }
        })
        
        if self.error_message:
            status_info["error"] = self.error_message
        
        if self.stop_time:
            status_info["stop_time"] = self.stop_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 获取任务统计
        if hasattr(self.dispatcher, 'get_statistics'):
            status_info["task_statistics"] = self.dispatcher.get_statistics()
        
        return status_info