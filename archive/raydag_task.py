from typing import Optional, Dict, Any
from sage.core.dag.ray.ray_dag import RayDAG

class RayDAGTask:
    """
    Ray DAG 任务包装器，用于与执行后端接口兼容
    """
    
    def __init__(self, ray_dag: RayDAG, execution_config: Optional[Dict[str, Any]] = None):
        """
        Initialize Ray DAG task.
        
        Args:
            ray_dag: The RayDAG to execute
            execution_config: Optional execution configuration
        """
        self.ray_dag = ray_dag
        self.execution_config = execution_config or {}
        self.task_type = "ray_dag"
    
    def get_dag(self) -> RayDAG:
        """Get the underlying RayDAG."""
        return self.ray_dag
    
    def get_config(self) -> Dict[str, Any]:
        """Get execution configuration."""
        return self.execution_config
    
    def __str__(self):
        return f"RayDAGTask(dag_id={self.ray_dag.id}, strategy={self.ray_dag.strategy})"


        
