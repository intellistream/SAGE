# Core API Components Tight Coupling with Kernel Layer Issue

## Problem Description

The current architecture exhibits poor separation of concerns between the core API components (`BaseOperator`, `BaseEnvironment`, `BaseFunction`) and the kernel runtime layer. Instead of providing a unified, clean API interface, these core components directly import and depend on numerous kernel implementation details, creating tight coupling and violating architectural boundaries.

## Current Coupling Issues

### 1. BaseOperator Direct Kernel Dependencies

`BaseOperator` directly imports from multiple kernel submodules:

```python
# From base_operator.py
from sage.kernel.runtime.task.base_task import BaseTask
from sage.utils.logging.custom_logger import CustomLogger
from sage.core.api.packet import Packet
from sage.kernel.runtime.communication.router.connection import Connection
from sage.kernel.runtime.task_context import TaskContext
from sage.core.factory.function_factory import FunctionFactory
from sage.kernel.runtime.communication.router.router import BaseRouter
```

**Issues:**
- Direct access to low-level communication components (router, packet, connection)
- Runtime implementation details exposed to core API
- Hard dependency on specific factory implementations
- Direct manipulation of kernel task objects

### 2. BaseEnvironment Kernel Integration Anti-patterns

`BaseEnvironment` tightly couples with kernel infrastructure:

```python
# From base_environment.py
from sage.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.jobmanager_client import JobManagerClient
from sage.core.factory.service_factory import ServiceFactory

# Direct factory instantiation
from sage.kernel.runtime.factory.service_task_factory import ServiceTaskFactory
service_task_factory = ServiceTaskFactory(
    service_factory=service_factory,
    remote=(self.platform == "remote")
)

# Direct jobmanager manipulation
from sage.kernel.jobmanager.utils.name_server import get_name
self.name = get_name(self.name)
```

**Issues:**
- Environment directly manages kernel factories
- JobManager client creation and lifecycle management scattered
- Service registration bypasses unified API layer
- Direct name server manipulation

### 3. BaseFunction Runtime Context Dependency

`BaseFunction` directly accesses kernel runtime:

```python
# From base_function.py
from sage.kernel.runtime.service.service_caller import ServiceManager, ServiceCallProxy
from sage.kernel.runtime.task_context import TaskContext
from sage.kernel.utils.persistence.state import load_function_state, save_function_state

# Direct runtime access
self.ctx: 'TaskContext' = None # Runtime injection
if self.ctx is None:
    raise RuntimeError("Runtime context not initialized. Cannot access services.")
```

**Issues:**
- Functions directly depend on TaskContext implementation
- Service calling mechanism tightly coupled with kernel runtime
- State management bypasses API abstraction

## Architectural Impact

### Current Problems:
1. **Testability**: Hard to unit test core components without kernel runtime
2. **Maintainability**: Changes in kernel affect core API components
3. **Extensibility**: Adding new runtimes requires modifying core components
4. **Modularity**: Core API cannot be used independently of kernel
5. **Interface Clarity**: No clear boundary between user API and implementation

### Missing Abstraction Layer:
The architecture lacks a unified kernel API facade that would:
- Provide consistent interface for all core components
- Hide implementation details of communication, factories, and runtime
- Enable swappable kernel implementations
- Centralize resource management

## Proposed Solution Architecture

### 1. Introduce Unified Kernel API Interface

Create `sage.kernel.api` module with clean interfaces:

```python
# sage/kernel/api/kernel_context.py
class KernelContext(ABC):
    @abstractmethod
    def get_logger(self) -> LoggerInterface: pass
    
    @abstractmethod
    def send_data(self, data: Any, target: str) -> bool: pass
    
    @abstractmethod
    def call_service(self, service_name: str, method: str, *args, **kwargs) -> Any: pass
    
    @abstractmethod 
    def save_state(self, state_data: dict) -> None: pass

# sage/kernel/api/environment_kernel.py  
class EnvironmentKernel(ABC):
    @abstractmethod
    def register_service(self, name: str, factory: ServiceFactory) -> None: pass
    
    @abstractmethod
    def submit_job(self, pipeline: List[Transformation]) -> JobHandle: pass
    
    @abstractmethod
    def get_client(self) -> ClientInterface: pass
```

### 2. Refactor Core Components

Update core components to depend only on kernel API interfaces:

```python
# BaseOperator refactor
class BaseOperator(ABC):
    def __init__(self, kernel_context: KernelContext, *args, **kwargs):
        self.kernel = kernel_context
        self.logger = kernel_context.get_logger()
        
    def send_data(self, data: Any, target: str = None):
        return self.kernel.send_data(data, target)

# BaseEnvironment refactor  
class BaseEnvironment(ABC):
    def __init__(self, name: str, config: dict, kernel: EnvironmentKernel):
        self.kernel = kernel
        self.logger = kernel.get_logger()
        
    def register_service(self, name: str, service_class: Type, *args, **kwargs):
        factory = ServiceFactory(service_class, *args, **kwargs)
        self.kernel.register_service(name, factory)
```

### 3. Implementation Strategy

1. **Phase 1**: Create kernel API interfaces without breaking existing code
2. **Phase 2**: Implement default kernel API implementation using current runtime
3. **Phase 3**: Gradually migrate core components to use kernel API
4. **Phase 4**: Remove direct kernel imports from core components
5. **Phase 5**: Add alternative kernel implementations for testing/different runtimes

## Benefits of Proposed Architecture

### 1. Clear Separation of Concerns
- Core API focused on user experience and business logic
- Kernel API focused on runtime implementation details
- Clean boundaries between layers

### 2. Improved Testability
- Core components testable with mock kernel implementations
- Unit tests independent of runtime infrastructure
- Integration tests clearly separated from unit tests

### 3. Enhanced Modularity
- Core API usable with different kernel implementations
- Kernel runtime interchangeable without affecting user code
- Plugin architecture for extending functionality

### 4. Better Maintainability  
- Changes in kernel implementation isolated from core API
- Cleaner interfaces reduce cognitive load
- Fewer cross-module dependencies

## Examples of Current Coupling Issues

### Issue 1: Operator Router Injection
```python
# Current problematic pattern in BaseOperator
def inject_router(self, router: 'BaseRouter'):
    self.router = router  # Direct kernel object injection
```
**Should be:**
```python
def set_kernel_context(self, context: KernelContext):
    self.kernel = context  # Clean API injection
```

### Issue 2: Environment Factory Management
```python
# Current problematic pattern in BaseEnvironment  
from sage.kernel.runtime.factory.service_task_factory import ServiceTaskFactory
service_task_factory = ServiceTaskFactory(...)  # Direct factory creation
```
**Should be:**
```python
def register_service(self, name: str, service_class: Type):
    self.kernel.register_service(name, service_class)  # Delegate to kernel API
```

### Issue 3: Function Context Dependency
```python
# Current problematic pattern in BaseFunction
self.ctx: 'TaskContext' = None  # Direct runtime context dependency
```
**Should be:**
```python
self.kernel: KernelContext = None  # Clean kernel interface dependency
```

## Acceptance Criteria

- [ ] Core API components (`BaseOperator`, `BaseEnvironment`, `BaseFunction`) have zero direct imports from `sage.kernel.runtime.*`
- [ ] All kernel interactions go through unified `sage.kernel.api` interfaces
- [ ] Core components are unit testable with mock kernel implementations
- [ ] Existing user code continues to work without changes
- [ ] Clear documentation of API boundaries and responsibilities
- [ ] Performance impact < 5% compared to current direct access patterns

## Related Issues

- Relates to #388 (StatefulFunction concept removal)
- Supports better service-to-service communication architecture
- Enables cleaner testing strategies across the framework

---

**Priority**: High
**Type**: Architecture/Refactoring  
**Effort**: Large (requires systematic refactoring across multiple components)
**Impact**: Framework-wide improvement in maintainability and testability
