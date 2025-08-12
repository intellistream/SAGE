# Factory层次重构设计 - 解决Core/Runtime依赖矛盾

## 问题根源分析

当前架构的核心问题是**创建职责**和**运行时注入职责**的混合，导致：

1. **循环依赖**：Core → Runtime → Core
2. **职责不清**：Factory既要了解Core对象结构，又要了解Runtime依赖
3. **测试困难**：无法独立测试Core层对象的创建

## 解决方案：三层Factory架构

### 1. 架构设计

```
Core Factory Layer (sage.core.factory/)
├── pure_operator_factory.py     # 纯粹的Operator创建
├── pure_function_factory.py     # 纯粹的Function创建  
└── core_factory_registry.py     # Core层Factory注册中心

Runtime Factory Layer (sage.kernel.runtime.factory/)
├── runtime_injector.py          # Runtime依赖注入器
├── context_factory.py           # Context创建工厂
└── integrated_factory.py        # 集成Factory（组合Core+Runtime）

Bridge Layer (sage.kernel.bridge/)
└── factory_coordinator.py       # 协调Core和Runtime层的Factory
```

### 2. 详细设计

#### 2.1 Core层 - 纯粹创建职责

```python
# sage/core/factory/pure_operator_factory.py
from abc import ABC, abstractmethod
from typing import Type, Any, Dict
from ..operator.base_operator import BaseOperator
from ..api.function.base_function import BaseFunction

class PureOperatorFactory(ABC):
    """纯粹的Operator工厂，不依赖任何Runtime组件"""
    
    def __init__(self, operator_class: Type[BaseOperator], function_instance: BaseFunction):
        self.operator_class = operator_class
        self.function_instance = function_instance
    
    def create_operator(self) -> BaseOperator:
        """创建纯净的Operator实例，无任何Runtime依赖"""
        operator = self.operator_class()
        operator.set_function(self.function_instance)  # 设置function，但不设置runtime依赖
        return operator

# sage/core/factory/pure_function_factory.py  
class PureFunctionFactory:
    """纯粹的Function工厂"""
    
    def __init__(self, function_class: Type[BaseFunction], *args, **kwargs):
        self.function_class = function_class
        self.args = args
        self.kwargs = kwargs
    
    def create_function(self) -> BaseFunction:
        """创建纯净的Function实例"""
        return self.function_class(*self.args, **self.kwargs)

# sage/core/factory/core_factory_registry.py
class CoreFactoryRegistry:
    """Core层Factory注册中心"""
    
    def __init__(self):
        self.operator_factories: Dict[str, PureOperatorFactory] = {}
        self.function_factories: Dict[str, PureFunctionFactory] = {}
    
    def register_operator_factory(self, name: str, factory: PureOperatorFactory):
        self.operator_factories[name] = factory
    
    def register_function_factory(self, name: str, factory: PureFunctionFactory):
        self.function_factories[name] = factory
    
    def create_operator(self, name: str) -> BaseOperator:
        return self.operator_factories[name].create_operator()
    
    def create_function(self, name: str) -> BaseFunction:
        return self.function_factories[name].create_function()
```

#### 2.2 Runtime层 - 依赖注入职责

```python
# sage/kernel/runtime/factory/runtime_injector.py
from abc import ABC, abstractmethod
from typing import Any
from ..task_context import TaskContext
from ...api.context.execution_context import ExecutionContext

class RuntimeInjector:
    """Runtime依赖注入器"""
    
    def __init__(self, context_factory: 'ContextFactory'):
        self.context_factory = context_factory
    
    def inject_operator_dependencies(self, operator: 'BaseOperator', context_config: Dict[str, Any]):
        """为Operator注入Runtime依赖"""
        execution_context = self.context_factory.create_execution_context(context_config)
        operator.set_execution_context(execution_context)
        
        # 为operator的function也注入依赖
        if operator.function:
            self.inject_function_dependencies(operator.function, context_config)
    
    def inject_function_dependencies(self, function: 'BaseFunction', context_config: Dict[str, Any]):
        """为Function注入Runtime依赖"""
        runtime_context = self.context_factory.create_runtime_context(context_config)
        function.set_runtime_context(runtime_context)

# sage/kernel/runtime/factory/context_factory.py
class ContextFactory:
    """Context创建工厂"""
    
    def create_execution_context(self, config: Dict[str, Any]) -> ExecutionContext:
        """创建执行上下文"""
        # 基于config创建具体的ExecutionContext实现
        return DefaultExecutionContext(config)
    
    def create_runtime_context(self, config: Dict[str, Any]) -> RuntimeContext:
        """创建运行时上下文"""
        return DefaultRuntimeContext(config)
    
    def create_task_context(self, config: Dict[str, Any]) -> TaskContext:
        """创建任务上下文（向后兼容）"""
        return TaskContext(**config)
```

#### 2.3 Bridge层 - 协调职责

```python
# sage/kernel/bridge/factory_coordinator.py
from typing import Type, Dict, Any
from ..core.factory.core_factory_registry import CoreFactoryRegistry
from ..kernel.runtime.factory.runtime_injector import RuntimeInjector
from ..kernel.runtime.factory.context_factory import ContextFactory

class FactoryCoordinator:
    """Factory协调器 - 连接Core和Runtime层"""
    
    def __init__(self):
        self.core_registry = CoreFactoryRegistry()
        self.context_factory = ContextFactory()
        self.runtime_injector = RuntimeInjector(self.context_factory)
    
    def create_operator_with_runtime(self, 
                                   operator_name: str,
                                   context_config: Dict[str, Any]) -> 'BaseOperator':
        """创建完整的Operator（Core创建 + Runtime注入）"""
        
        # Phase 1: Core层创建纯净对象
        operator = self.core_registry.create_operator(operator_name)
        
        # Phase 2: Runtime层注入依赖
        self.runtime_injector.inject_operator_dependencies(operator, context_config)
        
        return operator
    
    def create_function_with_runtime(self,
                                   function_name: str, 
                                   context_config: Dict[str, Any]) -> 'BaseFunction':
        """创建完整的Function（Core创建 + Runtime注入）"""
        
        # Phase 1: Core层创建纯净对象
        function = self.core_registry.create_function(function_name)
        
        # Phase 2: Runtime层注入依赖
        self.runtime_injector.inject_function_dependencies(function, context_config)
        
        return function
```

### 3. 重构后的对象设计

#### 3.1 BaseOperator重构

```python
# sage/core/operator/base_operator.py (重构后)
from abc import ABC, abstractmethod
from typing import Optional
from ..api.function.base_function import BaseFunction
from ...kernel.api.context.execution_context import ExecutionContext

class BaseOperator(ABC):
    def __init__(self):
        self.function: Optional[BaseFunction] = None
        self._execution_context: Optional[ExecutionContext] = None
    
    def set_function(self, function: BaseFunction):
        """设置function实例（Core层职责）"""
        self.function = function
    
    def set_execution_context(self, context: ExecutionContext):
        """设置执行上下文（Runtime层职责）"""
        self._execution_context = context
    
    @property
    def logger(self):
        """通过context获取logger"""
        if self._execution_context is None:
            return self._get_default_logger()
        return self._execution_context.logger
    
    @property
    def name(self) -> str:
        """获取名称"""
        if self._execution_context is None:
            return self.__class__.__name__
        return self._execution_context.name
    
    def send_data(self, data: Any, target: Optional[str] = None):
        """发送数据"""
        if self._execution_context is None:
            raise RuntimeError("Execution context not set")
        return self._execution_context.send_data(data, target)
    
    def save_state(self):
        """保存状态"""
        if self._execution_context is None or self.function is None:
            return
        if hasattr(self.function, 'get_state'):
            state = self.function.get_state()
            self._execution_context.state_manager.save_state(self.name, state)
    
    @abstractmethod
    def process_packet(self, packet):
        """处理数据包 - 子类实现"""
        pass
    
    def _get_default_logger(self):
        """获取默认logger（用于测试等场景）"""
        import logging
        return logging.getLogger(self.__class__.__name__)
```

#### 3.2 BaseFunction重构

```python
# sage/core/api/function/base_function.py (重构后)
from abc import ABC, abstractmethod
from typing import Optional
from ....kernel.api.context.runtime_context import RuntimeContext

class BaseFunction(ABC):
    def __init__(self, *args, **kwargs):
        self._runtime_context: Optional[RuntimeContext] = None
    
    def set_runtime_context(self, context: RuntimeContext):
        """设置运行时上下文（Runtime层职责）"""
        self._runtime_context = context
    
    @property
    def logger(self):
        """通过context获取logger"""
        if self._runtime_context is None:
            return self._get_default_logger()
        return self._runtime_context.logger
    
    @property
    def name(self):
        """获取名称"""
        if self._runtime_context is None:
            return self.__class__.__name__
        return self._runtime_context.name
    
    def call_service(self, service_name: str, method: str, *args, **kwargs):
        """调用服务"""
        if self._runtime_context is None:
            raise RuntimeError("Runtime context not set")
        return self._runtime_context.call_service(service_name, method, *args, **kwargs)
    
    def save_state(self, state: Any):
        """保存状态"""
        if self._runtime_context is None:
            raise RuntimeError("Runtime context not set")
        return self._runtime_context.state_manager.save_state(self.name, state)
    
    @abstractmethod
    def execute(self, data: Any):
        """执行逻辑 - 子类实现"""
        pass
    
    def _get_default_logger(self):
        """获取默认logger（用于测试等场景）"""
        import logging
        return logging.getLogger(self.__class__.__name__)
```

### 4. 使用示例

#### 4.1 在Transformation中的使用

```python
# sage/core/transformation/base_transformation.py (重构后)
class BaseTransformation:
    def __init__(self, env, function_class, *args, **kwargs):
        self.env = env
        self.function_class = function_class
        self.function_args = args
        self.function_kwargs = kwargs
        
        # 注册到Core层Factory Registry
        self._register_factories()
    
    def _register_factories(self):
        """注册Factory到Core层"""
        # 注册Function Factory
        function_factory = PureFunctionFactory(
            self.function_class, 
            *self.function_args, 
            **self.function_kwargs
        )
        core_registry.register_function_factory(self.basename + "_function", function_factory)
        
        # 注册Operator Factory
        function_instance = function_factory.create_function()
        operator_factory = PureOperatorFactory(self.operator_class, function_instance)
        core_registry.register_operator_factory(self.basename + "_operator", operator_factory)
```

#### 4.2 在Task创建中的使用

```python
# sage/kernel/runtime/task/task_creation.py
def create_task_with_operator(transformation_name: str, context_config: Dict[str, Any]):
    """使用新架构创建Task"""
    
    # 通过协调器创建完整的Operator
    coordinator = FactoryCoordinator()
    operator = coordinator.create_operator_with_runtime(
        transformation_name + "_operator",
        context_config
    )
    
    # 创建Task
    if context_config.get('remote', False):
        task = RayTask.remote(operator)
    else:
        task = LocalTask(operator)
    
    return task
```

### 5. 优势分析

#### 5.1 解决原问题
- **消除循环依赖**：Core层不再依赖Runtime层
- **职责清晰**：创建与注入分离
- **测试友好**：可以独立测试Core层对象

#### 5.2 新的优势
- **灵活性**：可以为同一个Core对象注入不同的Runtime依赖
- **可复用性**：Core Factory可以在不同Runtime环境下重用
- **可扩展性**：新的Runtime实现只需要实现新的Injector

#### 5.3 向后兼容
- **渐进迁移**：可以逐步迁移现有Factory
- **共存**：新旧Factory可以暂时共存
- **最小影响**：用户代码改动最小

## 总结

这个三层Factory架构彻底解决了您提出的核心矛盾：

1. **Core层Factory**：专注纯粹创建，无Runtime依赖
2. **Runtime层Injector**：专注依赖注入，无创建职责  
3. **Bridge层Coordinator**：协调两层，提供统一接口

这样既保持了职责的清晰分离，又提供了完整的功能，同时解决了测试和维护性问题。
