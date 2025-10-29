"""
SAGE Kernel Runtime - 流式执行引擎运行时

Layer: L3 (Kernel - Runtime Core)
Dependencies: sage.platform (L2), sage.common (L1)

运行时组件：
- JobManager: 作业管理器，协调任务执行
- Dispatcher: 任务分发器
- Task: 任务抽象（LocalTask, RayTask）
- Graph: 执行图（ExecutionGraph, GraphNode）
- Context: 执行上下文（TaskContext, ServiceContext）
- Communication: 通信层（Packet, Router, RPC）
- Service: 服务抽象（ServiceTask, ServiceCaller）
- Monitoring: 性能监控

Architecture:
- 提供流式数据处理的核心执行引擎
- 支持本地和分布式（Ray）两种执行模式
- 管理任务生命周期和数据流转
- 提供容错和监控能力

子模块：
- communication/: 进程间通信（队列、路由、RPC）
- context/: 执行上下文管理
- task/: 任务抽象和实现
- graph/: 执行图构建和管理
- service/: 服务节点管理
- factory/: 运行时对象工厂
- monitoring/: 性能监控和指标收集
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.kernel._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

__all__ = [
    "__version__",
    "__author__",
    "__email__",
]
