# [Refactoring] Extract call_service Implementation to Context Base Class

## 📋 Issue Summary

Currently, `BaseFunction` and `BaseService` both have nearly identical implementations of `call_service` and `call_service_async` properties, leading to significant code duplication. This violates the DRY (Don't Repeat Yourself) principle and makes maintenance difficult.

## 🔍 Current Code Duplication Analysis

### 1. Duplicated Code in BaseFunction and BaseService

**BaseFunction.call_service** (lines 40-68):
```python
@property
def call_service(self):
    if self.ctx is None:
        raise RuntimeError("Runtime context not initialized. Cannot access services.")
    
    if not hasattr(self, '_call_service_proxy') or self._call_service_proxy is None:
        from sage.kernel.runtime.service.service_caller import ServiceCallProxy
        
        class ServiceProxy:
            def __init__(self, service_manager: 'ServiceManager', logger=None):
                self._service_manager = service_manager
                self._service_proxies = {}  # 缓存ServiceCallProxy对象
                self.logger = logger if logger is not None else logging.getLogger(__name__)
                
            def __getitem__(self, service_name: str):
                if service_name not in self._service_proxies:
                    self._service_proxies[service_name] = ServiceCallProxy(
                        self._service_manager, service_name, logger=self.logger
                    )
                return self._service_proxies[service_name]
        
        self._call_service_proxy = ServiceProxy(self.ctx.service_manager, logger=self.logger)
    
    return self._call_service_proxy
```

**BaseService.call_service** (lines 39-67):
```python
@property
def call_service(self):
    if self.ctx is None:
        raise RuntimeError("Service context not initialized. Cannot access services.")
    
    if not hasattr(self, '_call_service_proxy') or self._call_service_proxy is None:
        from sage.kernel.runtime.service.service_caller import ServiceCallProxy
        
        class ServiceProxy:
            def __init__(self, service_manager: 'ServiceManager', logger=None):
                self._service_manager = service_manager
                self._service_proxies = {}  # 缓存ServiceCallProxy对象
                self.logger = logger if logger is not None else logging.getLogger(__name__)
                
            def __getitem__(self, service_name: str):
                if service_name not in self._service_proxies:
                    self._service_proxies[service_name] = ServiceCallProxy(
                        self._service_manager, service_name, logger=self.logger
                    )
                return self._service_proxies[service_name]
        
        self._call_service_proxy = ServiceProxy(self.ctx.service_manager, logger=self.logger)
    
    return self._call_service_proxy
```

### 2. Similar Duplication for call_service_async

Both classes also have nearly identical `call_service_async` implementations with the same pattern.

### 3. Context Dependencies

Both `TaskContext` and `ServiceContext` need to provide:
- `service_manager` property
- Logger access
- Runtime validation

## 🎯 Proposed Refactoring Solution

### Phase 1: Create Base Context Class

Create a new `BaseRuntimeContext` class that contains common functionality:

```python
# /packages/sage-kernel/src/sage/kernel/runtime/base_context.py
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from sage.kernel.runtime.service.service_caller import ServiceManager
    from sage.kernel.utils.logging.custom_logger import CustomLogger

class BaseRuntimeContext(ABC):
    """
    Base runtime context class providing common functionality
    for TaskContext and ServiceContext
    """
    
    def __init__(self):
        self._service_manager: Optional['ServiceManager'] = None
        self._call_service_proxy = None
        self._call_service_async_proxy = None
    
    @property
    @abstractmethod
    def logger(self) -> 'CustomLogger':
        """Logger property - must be implemented by subclasses"""
        pass
    
    @property
    def service_manager(self) -> 'ServiceManager':
        """Lazy-loaded service manager"""
        if self._service_manager is None:
            from sage.kernel.runtime.service.service_caller import ServiceManager
            self._service_manager = ServiceManager(self, logger=self.logger)
        return self._service_manager
    
    @property
    def call_service(self):
        """
        Synchronous service call syntax sugar
        Usage: self.call_service["service_name"].method(*args)
        """
        if not hasattr(self, '_call_service_proxy') or self._call_service_proxy is None:
            from sage.kernel.runtime.service.service_caller import ServiceCallProxy
            
            class ServiceProxy:
                def __init__(self, service_manager: 'ServiceManager', logger=None):
                    self._service_manager = service_manager
                    self._service_proxies = {}
                    self.logger = logger if logger is not None else logging.getLogger(__name__)
                    
                def __getitem__(self, service_name: str):
                    if service_name not in self._service_proxies:
                        self._service_proxies[service_name] = ServiceCallProxy(
                            self._service_manager, service_name, logger=self.logger
                        )
                    return self._service_proxies[service_name]
            
            self._call_service_proxy = ServiceProxy(self.service_manager, logger=self.logger)
        
        return self._call_service_proxy
    
    @property 
    def call_service_async(self):
        """
        Asynchronous service call syntax sugar
        Usage: future = self.call_service_async["service_name"].method(*args)
        """
        if not hasattr(self, '_call_service_async_proxy') or self._call_service_async_proxy is None:
            class AsyncServiceProxy:
                def __init__(self, service_manager: 'ServiceManager', logger=None):
                    self._service_manager = service_manager
                    self._async_service_proxies = {}
                    self.logger = logger if logger is not None else logging.getLogger(__name__)
                    
                def __getitem__(self, service_name: str):
                    if service_name not in self._async_service_proxies:
                        from sage.kernel.runtime.service.service_caller import ServiceCallProxy
                        self._async_service_proxies[service_name] = ServiceCallProxy(
                            self._service_manager, service_name, logger=self.logger
                        )
                    return self._async_service_proxies[service_name]
            
            self._call_service_async_proxy = AsyncServiceProxy(self.service_manager, logger=self.logger)
        
        return self._call_service_async_proxy
```

### Phase 2: Create Context Mixin for Functions/Services

Create a mixin that can be used by both `BaseFunction` and `BaseService`:

```python
# /packages/sage-kernel/src/sage/core/api/mixins/service_call_mixin.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sage.kernel.runtime.base_context import BaseRuntimeContext

class ServiceCallMixin:
    """
    Mixin providing service call capabilities for Functions and Services
    Requires the class to have a 'ctx' attribute of type BaseRuntimeContext
    """
    
    @property
    def call_service(self):
        """
        Synchronous service call syntax sugar
        Usage: self.call_service["service_name"].method(*args)
        """
        if not hasattr(self, 'ctx') or self.ctx is None:
            raise RuntimeError("Runtime context not initialized. Cannot access services.")
        
        return self.ctx.call_service
    
    @property
    def call_service_async(self):
        """
        Asynchronous service call syntax sugar
        Usage: future = self.call_service_async["service_name"].method(*args)
        """
        if not hasattr(self, 'ctx') or self.ctx is None:
            raise RuntimeError("Runtime context not initialized. Cannot access services.")
        
        return self.ctx.call_service_async
```

### Phase 3: Update Context Classes

Update `TaskContext` and `ServiceContext` to inherit from `BaseRuntimeContext`:

```python
# TaskContext changes
class TaskContext(BaseRuntimeContext):
    def __init__(self, ...):
        super().__init__()  # Initialize base context
        # ... existing initialization code
    
    # Remove service_manager property (inherited from base)

# ServiceContext changes  
class ServiceContext(BaseRuntimeContext):
    def __init__(self, ...):
        super().__init__()  # Initialize base context
        # ... existing initialization code
    
    # Remove service_manager property (inherited from base)
```

### Phase 4: Update Function and Service Classes

Update `BaseFunction` and `BaseService` to use the mixin:

```python
# BaseFunction changes
class BaseFunction(ServiceCallMixin, ABC):
    # Remove call_service and call_service_async properties
    # They are now provided by ServiceCallMixin

# BaseService changes  
class BaseService(ServiceCallMixin, ABC):
    # Remove call_service and call_service_async properties
    # They are now provided by ServiceCallMixin
```

## 📊 Expected Benefits

### 1. Code Reduction
- **Eliminate ~60 lines** of duplicated code between BaseFunction and BaseService
- **Single source of truth** for service call implementation
- **Easier maintenance** - changes only need to be made in one place

### 2. Better Architecture
- **Clear separation of concerns**: Context handles service management, Mixin provides interface
- **Reusable components**: Other classes can easily get service call capabilities  
- **Consistent behavior**: Guaranteed identical behavior across Functions and Services

### 3. Extensibility
- **Easy to add new features** to service calling (logging, metrics, etc.)
- **Simple to create new types** that need service call capabilities
- **Modular design** allows for better testing and composition

## 🧪 Implementation Strategy

### Step 1: Create Base Classes
- [ ] Create `BaseRuntimeContext` with common service call logic
- [ ] Create `ServiceCallMixin` for function/service interface
- [ ] Add comprehensive unit tests

### Step 2: Update Context Classes  
- [ ] Make `TaskContext` inherit from `BaseRuntimeContext`
- [ ] Make `ServiceContext` inherit from `BaseRuntimeContext` 
- [ ] Remove duplicated `service_manager` implementations
- [ ] Update tests

### Step 3: Update Function/Service Classes
- [ ] Make `BaseFunction` use `ServiceCallMixin`
- [ ] Make `BaseService` use `ServiceCallMixin`
- [ ] Remove duplicated `call_service` implementations
- [ ] Update tests

### Step 4: Verification
- [ ] Ensure all existing functionality works unchanged
- [ ] Verify service-to-service communication still works
- [ ] Run full integration tests
- [ ] Performance regression testing

## 📝 Implementation Notes

### Files to Create
1. `/packages/sage-kernel/src/sage/kernel/runtime/base_context.py`
2. `/packages/sage-kernel/src/sage/core/api/mixins/service_call_mixin.py`

### Files to Modify
1. `/packages/sage-kernel/src/sage/kernel/runtime/task_context.py`
2. `/packages/sage-kernel/src/sage/kernel/runtime/service_context.py`  
3. `/packages/sage-kernel/src/sage/core/api/function/base_function.py`
4. `/packages/sage-kernel/src/sage/core/api/service/base_service.py`

### Backward Compatibility
- **Zero breaking changes** for existing code
- All existing APIs remain the same
- Same usage patterns: `self.call_service["name"].method()`

### Testing Strategy
- **Unit tests** for new base classes and mixin
- **Integration tests** for context inheritance
- **Functional tests** for service calling behavior
- **Regression tests** to ensure no functionality is broken

---

**Priority**: Medium-High
**Complexity**: Medium (Refactoring existing working code)
**Impact**: High (Eliminates code duplication, improves maintainability)
**Risk**: Low (Internal refactoring with same external API)
**Dependencies**: None (can be done incrementally)
