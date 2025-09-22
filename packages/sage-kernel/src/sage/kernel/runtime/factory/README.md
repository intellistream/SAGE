# Runtime Factory 模块

Runtime Factory 模块提供各种运行时组件的工厂类，负责创建和管理任务、算子、函数和服务等核心组件。

## 模块架构

### 核心工厂类

- **`function_factory.py`**: 函数工厂
  - `FunctionFactory`: 创建和管理函数实例
  - 支持函数参数和上下文注入
  - 提供函数实例的生命周期管理

- **`operator_factory.py`**: 算子工厂
  - `OperatorFactory`: 创建各种类型的算子实例
  - 整合函数工厂和运行时上下文
  - 支持本地和远程算子实例化

- **`task_factory.py`**: 任务工厂
  - `TaskFactory`: 创建本地和远程任务实例
  - 支持 Ray Actor 和本地线程任务
  - 管理任务的分布式部署

- **`service_factory.py`**: 服务工厂
  - 创建各种类型的服务实例
  - 支持本地和分布式服务部署

- **`service_task_factory.py`**: 服务任务工厂
  - 专门用于创建服务相关的任务实例
  - 整合服务调用和任务执行

## 核心功能

### 1. 函数实例化
```python
from sage.kernels.runtime.factory.function_factory import FunctionFactory

# 创建函数工厂
factory = FunctionFactory(
    function_class=MyFunction,
    function_args=(arg1, arg2),
    function_kwargs={"param": "value"}
)

# 创建函数实例
function = factory.create_function("my_function", runtime_context)
```

### 2. 算子创建
```python
from sage.kernels.runtime.factory.operator_factory import OperatorFactory

# 创建算子工厂
operator_factory = OperatorFactory(
    operator_class=MyOperator,
    function_factory=function_factory,
    basename="my_operator",
    env_name="production"
)

# 创建算子实例
operator = operator_factory.create_operator(runtime_context)
```

### 3. 任务部署
```python
from sage.kernels.runtime.factory.task_factory import TaskFactory

# 创建任务工厂
task_factory = TaskFactory(transformation=transformation)

# 创建本地任务
local_task = task_factory.create_task("local_task", runtime_context)

# 创建远程任务（Ray Actor）
remote_task = task_factory.create_task("remote_task", runtime_context)
```

## 工厂模式特性

### 配置驱动创建
- **参数化配置**: 支持通过配置参数创建不同类型的实例
- **环境适配**: 根据运行环境自动选择合适的实现
- **资源管理**: 统一管理组件的资源分配和回收

### 依赖注入
- **上下文注入**: 自动注入运行时上下文
- **参数传递**: 支持构造函数参数的灵活传递
- **配置绑定**: 将配置参数绑定到组件实例

### 生命周期管理
- **延迟创建**: 支持组件的延迟实例化
- **单例模式**: 对需要的组件提供单例支持
- **资源清理**: 自动管理组件的资源清理

## 分布式支持

### 本地模式
```python
# 创建本地任务
task_factory = TaskFactory(transformation)
task_factory.remote = False
local_task = task_factory.create_task("local", ctx)
```

### 远程模式 (Ray)
```python
# 创建远程任务
task_factory = TaskFactory(transformation)
task_factory.remote = True
ray_task = task_factory.create_task("remote", ctx)
```

### Actor 包装
- **ActorWrapper**: 提供统一的 Actor 接口
- **生命周期管理**: 管理 Ray Actor 的创建和销毁
- **故障恢复**: 支持 Actor 的自动故障恢复

## 组件类型

### 函数组件
- **用户函数**: 用户定义的业务逻辑函数
- **内置函数**: 框架提供的标准函数
- **扩展函数**: 第三方提供的扩展函数

### 算子组件
- **Source**: 数据源算子
- **Transform**: 数据转换算子
- **Sink**: 数据输出算子
- **Window**: 窗口算子

### 任务组件
- **LocalTask**: 本地线程任务
- **RayTask**: Ray Actor 任务
- **ServiceTask**: 服务调用任务

## 配置管理

### 工厂配置
```python
factory_config = {
    "function": {
        "class": "MyFunction",
        "args": [arg1, arg2],
        "kwargs": {"param": "value"}
    },
    "operator": {
        "class": "MyOperator",
        "basename": "my_op",
        "remote": False
    },
    "task": {
        "remote": True,
        "parallelism": 4
    }
}
```

### 环境适配
- **开发环境**: 使用本地组件便于调试
- **测试环境**: 使用轻量级分布式部署
- **生产环境**: 使用完整的分布式集群

## 扩展接口

### 自定义工厂
```python
class CustomFactory:
    def __init__(self, config):
        self.config = config
    
    def create_instance(self, name, context):
        # 实现自定义创建逻辑
        return self.build_component(name, context)
```

### 工厂注册
```python
# 注册自定义工厂
factory_registry.register("custom", CustomFactory)

# 使用注册的工厂
factory = factory_registry.get("custom")
instance = factory.create_instance("my_component", ctx)
```

## 性能优化

### 对象池
- **实例复用**: 复用创建成本高的组件实例
- **内存管理**: 优化内存使用避免频繁创建销毁
- **预热机制**: 预先创建常用组件实例

### 延迟加载
- **按需创建**: 只在需要时创建组件实例
- **配置验证**: 延迟到使用时才进行配置验证
- **资源节约**: 避免不必要的资源消耗

## 错误处理

### 创建失败
- **参数验证**: 创建前验证参数的有效性
- **异常处理**: 优雅处理创建过程中的异常
- **回退机制**: 提供默认实现作为回退

### 依赖检查
- **依赖验证**: 检查组件依赖是否满足
- **版本兼容**: 验证组件版本兼容性
- **环境检查**: 确保运行环境满足要求

## 参考

相关模块：
- `../task/`: 任务执行系统
- `../service/`: 服务调用框架
- `../../core/`: 核心组件定义
