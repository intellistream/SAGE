# SAGE Kernel API Interface 设计草案

## 概览

基于对sage.core和kernel源码的深入分析，当前架构存在严重的紧耦合问题：

### 当前耦合分析：

1. **BaseOperator的kernel依赖**:
   - 直接引入并操作`TaskContext`, `BaseRouter`, `Packet`, `Connection`
   - 通过`inject_router()`方法直接接收kernel runtime对象
   - 直接使用`FunctionFactory`创建function实例

2. **BaseEnvironment的kernel集成**:
   - 直接创建和管理`ServiceTaskFactory`, `JobManagerClient`
   - 通过`register_service()`直接操作kernel factories
   - 直接调用`jobmanager.submit_job()`方法

3. **BaseFunction的runtime依赖**:
   - 通过`ctx: TaskContext`直接访问kernel runtime
   - 使用`self.ctx.call_service`进行服务调用
   - 通过`load_function_state/save_function_state`直接访问持久化

4. **Transformation的工厂依赖**:
   - 直接创建和管理`OperatorFactory`, `FunctionFactory`, `TaskFactory`
   - 通过工厂直接与kernel runtime交互

## Kernel API Interface 架构设计

### 1. 核心设计原则

- **单一职责**: 每个接口专注特定功能域
- **依赖倒置**: Core API只依赖抽象接口，不依赖具体实现
- **接口隔离**: 提供最小化、专用的接口
- **替换性**: 支持不同kernel实现的无缝切换

### 2. 接口层次结构

```
sage.kernel.api/
├── context/
│   ├── runtime_context.py       # 运行时上下文抽象接口
│   ├── execution_context.py     # 执行上下文抽象接口
│   └── service_context.py       # 服务上下文抽象接口
├── communication/
│   ├── message_router.py        # 消息路由抽象接口
│   ├── data_transport.py        # 数据传输抽象接口
│   └── queue_manager.py         # 队列管理抽象接口
├── lifecycle/
│   ├── job_manager.py           # 作业管理抽象接口
│   ├── task_manager.py          # 任务管理抽象接口
│   └── service_manager.py       # 服务管理抽象接口
├── storage/
│   ├── state_manager.py         # 状态管理抽象接口
│   └── checkpoint_manager.py    # 检查点管理抽象接口
├── logging/
│   └── logger_factory.py        # 日志工厂抽象接口
└── kernel_facade.py             # 统一Kernel门面接口
```

### 3. 详细接口设计

#### 3.1 运行时上下文接口

```python
# sage/kernel/api/context/runtime_context.py
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from ..communication.data_transport import DataTransport
from ..logging.logger_factory import LoggerFactory
from ..storage.state_manager import StateManager

class RuntimeContext(ABC):
    """运行时上下文抽象接口"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """获取运行时名称"""
        pass
    
    @property
    @abstractmethod
    def logger(self) -> 'Logger':
        """获取日志记录器"""
        pass
    
    @property
    @abstractmethod
    def transport(self) -> DataTransport:
        """获取数据传输接口"""
        pass
    
    @property
    @abstractmethod
    def state_manager(self) -> StateManager:
        """获取状态管理器"""
        pass
    
    @abstractmethod
    def call_service(self, service_name: str, method: str, *args, **kwargs) -> Any:
        """同步服务调用"""
        pass
    
    @abstractmethod
    def call_service_async(self, service_name: str, method: str, *args, **kwargs) -> 'Future':
        """异步服务调用"""
        pass
    
    @abstractmethod
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        pass

# sage/kernel/api/context/execution_context.py
class ExecutionContext(RuntimeContext):
    """执行上下文接口 - 用于Operator和Function"""
    
    @abstractmethod
    def send_data(self, data: Any, target: Optional[str] = None, 
                  partition_key: Optional[Any] = None) -> bool:
        """发送数据到下游"""
        pass
    
    @abstractmethod
    def get_parallel_index(self) -> int:
        """获取并行索引"""
        pass
    
    @abstractmethod
    def get_parallelism(self) -> int:
        """获取并行度"""
        pass
    
    @abstractmethod
    def is_source(self) -> bool:
        """判断是否为源任务"""
        pass
    
    @abstractmethod
    def should_stop(self) -> bool:
        """检查是否应该停止执行"""
        pass
```

#### 3.2 通信接口

```python
# sage/kernel/api/communication/data_transport.py
from abc import ABC, abstractmethod
from typing import Any, Optional, List

class DataTransport(ABC):
    """数据传输抽象接口"""
    
    @abstractmethod
    def send(self, data: Any, target: Optional[str] = None, 
             partition_key: Optional[Any] = None, 
             partition_strategy: Optional[str] = None) -> bool:
        """发送数据"""
        pass
    
    @abstractmethod
    def broadcast(self, data: Any) -> bool:
        """广播数据"""
        pass
    
    @abstractmethod
    def set_downstream_connections(self, connections: List['ConnectionInfo']) -> None:
        """设置下游连接"""
        pass

# sage/kernel/api/communication/message_router.py
class MessageRouter(ABC):
    """消息路由抽象接口"""
    
    @abstractmethod
    def route_by_key(self, data: Any, key: Any) -> str:
        """基于key路由"""
        pass
    
    @abstractmethod
    def route_round_robin(self, data: Any) -> str:
        """轮询路由"""
        pass
    
    @abstractmethod
    def route_broadcast(self, data: Any) -> List[str]:
        """广播路由"""
        pass
```

#### 3.3 生命周期管理接口

```python
# sage/kernel/api/lifecycle/job_manager.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..context.runtime_context import RuntimeContext

class JobManager(ABC):
    """作业管理抽象接口"""
    
    @abstractmethod
    def submit_job(self, pipeline_config: Dict[str, Any]) -> str:
        """提交作业，返回作业ID"""
        pass
    
    @abstractmethod
    def cancel_job(self, job_id: str) -> bool:
        """取消作业"""
        pass
    
    @abstractmethod
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """获取作业状态"""
        pass
    
    @abstractmethod
    def register_service_factory(self, name: str, factory_config: Dict[str, Any]) -> None:
        """注册服务工厂"""
        pass

# sage/kernel/api/lifecycle/service_manager.py
class ServiceManager(ABC):
    """服务管理抽象接口"""
    
    @abstractmethod
    def register_service(self, name: str, service_class: type, *args, **kwargs) -> None:
        """注册服务"""
        pass
    
    @abstractmethod
    def start_service(self, name: str) -> bool:
        """启动服务"""
        pass
    
    @abstractmethod
    def stop_service(self, name: str) -> bool:
        """停止服务"""
        pass
    
    @abstractmethod
    def call_service(self, name: str, method: str, *args, **kwargs) -> Any:
        """调用服务方法"""
        pass
```

#### 3.4 存储接口

```python
# sage/kernel/api/storage/state_manager.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class StateManager(ABC):
    """状态管理抽象接口"""
    
    @abstractmethod
    def save_state(self, key: str, state: Any) -> bool:
        """保存状态"""
        pass
    
    @abstractmethod
    def load_state(self, key: str, default: Any = None) -> Any:
        """加载状态"""
        pass
    
    @abstractmethod
    def clear_state(self, key: str) -> bool:
        """清除状态"""
        pass
    
    @abstractmethod
    def create_checkpoint(self, checkpoint_id: str) -> bool:
        """创建检查点"""
        pass
    
    @abstractmethod
    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """恢复检查点"""
        pass
```

#### 3.5 统一Kernel门面

```python
# sage/kernel/api/kernel_facade.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .context.execution_context import ExecutionContext
from .context.runtime_context import RuntimeContext
from .lifecycle.job_manager import JobManager
from .lifecycle.service_manager import ServiceManager
from .logging.logger_factory import LoggerFactory

class KernelFacade(ABC):
    """Kernel统一门面接口"""
    
    @abstractmethod
    def create_execution_context(self, config: Dict[str, Any]) -> ExecutionContext:
        """创建执行上下文"""
        pass
    
    @abstractmethod
    def create_runtime_context(self, config: Dict[str, Any]) -> RuntimeContext:
        """创建运行时上下文"""
        pass
    
    @property
    @abstractmethod
    def job_manager(self) -> JobManager:
        """获取作业管理器"""
        pass
    
    @property
    @abstractmethod
    def service_manager(self) -> ServiceManager:
        """获取服务管理器"""
        pass
    
    @property
    @abstractmethod
    def logger_factory(self) -> LoggerFactory:
        """获取日志工厂"""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """关闭kernel"""
        pass
```

### 4. Core API重构示例

#### 4.1 BaseOperator重构

```python
# 重构后的BaseOperator
class BaseOperator(ABC):
    def __init__(self, execution_context: ExecutionContext, 
                 function_class: Type['BaseFunction'], *args, **kwargs):
        
        self.context = execution_context
        self.logger = execution_context.logger
        
        # 通过context创建function实例，而不是直接使用factory
        self.function = self._create_function(function_class, *args, **kwargs)

    def _create_function(self, function_class: Type['BaseFunction'], *args, **kwargs):
        """通过context创建function实例"""
        function = function_class(*args, **kwargs)
        function.set_context(self.context)  # 注入context而不是直接设置ctx
        return function

    def send_data(self, data: Any, target: Optional[str] = None, 
                  partition_key: Optional[Any] = None):
        """通过context发送数据"""
        return self.context.send_data(data, target, partition_key)

    def save_state(self):
        """通过context保存状态"""
        if hasattr(self.function, 'get_state'):
            state = self.function.get_state()
            self.context.state_manager.save_state(self.context.name, state)
    
    # 移除inject_router等直接kernel依赖方法
```

#### 4.2 BaseEnvironment重构

```python
# 重构后的BaseEnvironment
class BaseEnvironment(ABC):
    def __init__(self, name: str, config: dict, kernel: KernelFacade):
        self.name = name
        self.config = config
        self.kernel = kernel
        self.logger = kernel.logger_factory.get_logger(name)
        
        self.pipeline: List[BaseTransformation] = []

    def register_service(self, service_name: str, service_class: Type, *args, **kwargs):
        """通过kernel门面注册服务"""
        self.kernel.service_manager.register_service(
            service_name, service_class, *args, **kwargs
        )
        self.logger.info(f"Registered service: {service_name}")

    def submit(self):
        """通过kernel门面提交作业"""
        pipeline_config = self._build_pipeline_config()
        job_id = self.kernel.job_manager.submit_job(pipeline_config)
        self.uuid = job_id
        self.logger.info(f"Submitted job with ID: {job_id}")
        return job_id

    def _build_pipeline_config(self) -> Dict[str, Any]:
        """构建pipeline配置，而不是直接传递transformation对象"""
        return {
            'name': self.name,
            'config': self.config,
            'transformations': [
                {
                    'id': trans.basename,
                    'function_class': trans.function_class.__name__,
                    'function_module': trans.function_class.__module__,
                    'args': trans.function_args,
                    'kwargs': trans.function_kwargs,
                    'parallelism': trans.parallelism,
                    'operator_class': trans.operator_class.__name__,
                    'upstreams': [up.basename for up in trans.upstreams],
                    'downstreams': trans.downstreams
                }
                for trans in self.pipeline
            ]
        }
```

#### 4.3 BaseFunction重构

```python
# 重构后的BaseFunction
class BaseFunction(ABC):
    def __init__(self, *args, **kwargs):
        self._context: Optional[RuntimeContext] = None

    def set_context(self, context: RuntimeContext):
        """设置运行时上下文"""
        self._context = context

    @property
    def logger(self):
        """通过context获取logger"""
        if self._context is None:
            return logging.getLogger(self.__class__.__name__)
        return self._context.logger

    @property
    def name(self):
        """通过context获取名称"""
        if self._context is None:
            return self.__class__.__name__
        return self._context.name

    def call_service(self, service_name: str, method: str, *args, **kwargs) -> Any:
        """通过context调用服务"""
        if self._context is None:
            raise RuntimeError("Runtime context not initialized")
        return self._context.call_service(service_name, method, *args, **kwargs)

    def call_service_async(self, service_name: str, method: str, *args, **kwargs):
        """通过context异步调用服务"""
        if self._context is None:
            raise RuntimeError("Runtime context not initialized")
        return self._context.call_service_async(service_name, method, *args, **kwargs)

    def save_state(self, state: Any):
        """通过context保存状态"""
        if self._context is None:
            raise RuntimeError("Runtime context not initialized")
        return self._context.state_manager.save_state(self.name, state)

    def load_state(self, default: Any = None) -> Any:
        """通过context加载状态"""
        if self._context is None:
            raise RuntimeError("Runtime context not initialized")
        return self._context.state_manager.load_state(self.name, default)
```

### 5. 实现策略

#### Phase 1: 创建接口层（不破坏现有代码）
- 在`sage/kernel/api/`下创建所有接口定义
- 不修改任何现有代码
- 添加完整的文档和示例

#### Phase 2: 实现Default Kernel适配器
- 创建`DefaultKernelFacade`实现所有接口
- 使用现有kernel runtime作为后端
- 提供向后兼容的适配器

#### Phase 3: 逐步迁移Core API
- 先迁移BaseFunction（影响最小）
- 再迁移BaseOperator
- 最后迁移BaseEnvironment
- 每个组件保持向后兼容

#### Phase 4: 清理和优化
- 移除旧的直接依赖
- 优化接口实现
- 添加测试支持

### 6. 测试策略

#### Mock Kernel实现
```python
# tests/mock_kernel/mock_kernel_facade.py
class MockKernelFacade(KernelFacade):
    """用于测试的Mock Kernel实现"""
    
    def __init__(self):
        self.services = {}
        self.jobs = {}
        self.states = {}
        
    def create_execution_context(self, config):
        return MockExecutionContext(config, self)
    
    # ... 其他mock实现
```

#### 单元测试示例
```python
# 测试BaseFunction而不需要真实的kernel runtime
def test_base_function_service_call():
    mock_kernel = MockKernelFacade()
    mock_context = mock_kernel.create_runtime_context({'name': 'test'})
    
    function = MyFunction()
    function.set_context(mock_context)
    
    # 测试服务调用
    result = function.call_service('test_service', 'test_method')
    assert result is not None
```

### 7. 迁移后的架构优势

#### 7.1 解耦合
- Core API完全不依赖kernel实现细节
- 支持不同kernel后端的无缝切换
- 清晰的接口边界

#### 7.2 可测试性
- 每个组件可以独立测试
- Mock实现简化单元测试
- 集成测试与单元测试分离

#### 7.3 可扩展性
- 新的kernel实现只需实现接口
- 支持插件架构
- 功能可以独立演进

#### 7.4 维护性
- 接口变更影响最小化
- 代码职责更加清晰
- 降低认知负担

## 总结

这个Kernel API Interface设计通过引入清晰的抽象层，彻底解决了当前sage.core组件与kernel runtime的紧耦合问题。通过分层的接口设计和渐进式迁移策略，可以在不破坏现有代码的前提下，实现架构的全面重构，大幅提升系统的可测试性、可维护性和可扩展性。
