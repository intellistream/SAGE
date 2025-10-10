"""
调度器实现模板

使用这个模板快速实现新的调度策略进行对比实验。

重要原则：
1. 调度器在 Environment 级别配置
2. 并行度在 operator 级别（transformation.parallelism）
3. 调度器负责决策何时、如何调度任务

使用方法:
1. 复制这个文件并重命名（例如：priority_scheduler.py）
2. 替换 TemplateScheduler 为你的调度器名称
3. 实现 schedule_task() 中的调度逻辑
4. 在 impl/__init__.py 中导出
5. 通过 Environment(scheduler=YourScheduler()) 使用
"""

from typing import TYPE_CHECKING, Dict, Any
import time

from sage.kernel.scheduler.api import BaseScheduler

if TYPE_CHECKING:
    from sage.kernel.runtime.graph.graph_node import TaskNode
    from sage.kernel.runtime.graph.service_node import ServiceNode
    from sage.kernel.runtime.task.base_task import BaseTask
    from sage.kernel.runtime.service.base_service_task import BaseServiceTask


class TemplateScheduler(BaseScheduler):
    """
    [你的调度器名称] Scheduler
    
    [描述你的调度策略]
    
    特点：
    - [特点 1]
    - [特点 2]
    
    适用场景：
    - [场景 1]
    - [场景 2]
    
    使用方式:
        env = LocalEnvironment(scheduler=TemplateScheduler())
        (env.from_source(MySource)
            .map(MyOperator, parallelism=4)
            .sink(MySink))
        env.submit()
    """
    
    def __init__(self, platform: str = "local", **kwargs):
        """
        初始化调度器
        
        Args:
            platform: 平台类型 ('local' 或 'remote')
            **kwargs: 调度器特定的参数
        """
        self.platform = platform
        
        # 调度器状态
        self.scheduled_count = 0
        self.metrics = {}
    
    def schedule_task(self, task_node: "TaskNode", runtime_ctx=None) -> "BaseTask":
        """
        调度任务节点
        
        核心逻辑：
        1. 从 task_node.transformation 获取 operator 信息
        2. task_node.transformation.parallelism 包含并行度设置
        3. 根据你的调度算法做出决策
        4. 创建并返回任务实例
        
        Args:
            task_node: 任务节点（包含 transformation 和 parallelism 信息）
            runtime_ctx: 运行时上下文
            
        Returns:
            创建的任务实例
        """
        start_time = time.time()
        
        # 步骤 1: 获取 transformation 信息
        transformation = task_node.transformation
        parallelism = getattr(transformation, 'parallelism', 1)
        
        # 步骤 2: 实现你的调度逻辑
        # 例如：
        # - 根据 parallelism 决定资源分配
        # - 根据系统负载决定调度时机
        # - 根据任务类型优先级排序
        self._apply_scheduling_logic(task_node, parallelism)
        
        # 步骤 3: 创建任务
        ctx = runtime_ctx if runtime_ctx is not None else task_node.ctx
        task = task_node.task_factory.create_task(task_node.name, ctx)
        
        # 步骤 4: 记录指标（用于对比不同调度策略）
        self.scheduled_count += 1
        elapsed = time.time() - start_time
        self._update_metrics(task_node.name, elapsed, parallelism)
        
        return task
    
    def _apply_scheduling_logic(self, task_node: "TaskNode", parallelism: int):
        """
        应用你的调度逻辑
        
        Args:
            task_node: 任务节点
            parallelism: 并行度
        """
        # 实现你的核心调度算法
        # 例如：
        # if parallelism > 4:
        #     # 高并行度任务的特殊处理
        #     pass
        pass
    
    def _update_metrics(self, task_name: str, elapsed: float, parallelism: int):
        """
        更新调度指标
        
        Args:
            task_name: 任务名
            elapsed: 调度耗时
            parallelism: 并行度
        """
        if task_name not in self.metrics:
            self.metrics[task_name] = {
                "count": 0,
                "total_time": 0.0,
                "parallelism": parallelism
            }
        
        self.metrics[task_name]["count"] += 1
        self.metrics[task_name]["total_time"] += elapsed
    
    def schedule_service(self, service_node: "ServiceNode", runtime_ctx=None) -> "BaseServiceTask":
        """
        调度服务节点
        
        Args:
            service_node: 服务节点
            runtime_ctx: 运行时上下文
            
        Returns:
            创建的服务任务实例
        """
        ctx = runtime_ctx if runtime_ctx is not None else service_node.ctx
        service_task = service_node.service_task_factory.create_service_task(ctx)
        return service_task
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        获取调度器性能指标（供开发者对比不同策略）
        
        Returns:
            指标字典
        """
        return {
            "scheduler_type": "Template",
            "total_scheduled": self.scheduled_count,
            "platform": self.platform,
            "detailed_metrics": self.metrics,
        }
    
    def shutdown(self):
        """关闭调度器，释放资源"""
        self.metrics.clear()


__all__ = ["TemplateScheduler"]
