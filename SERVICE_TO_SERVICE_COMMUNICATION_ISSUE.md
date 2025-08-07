# [Feature Request] Enable Service-to-Service Communication in SAGE Architecture

## 📋 Issue Summary

Currently, only `BaseFunction` (operators/transformations) can call services through the `call_service` mechanism. However, services themselves (derived from `BaseServiceTask`) cannot easily call other services. We need to enable service-to-service communication to allow services like `MemoryService` to call other microservices like `KVService` and `VDBService`.

## 🎯 Objective

Enable services to call other services with the same convenience and reliability as functions, by extending the service communication infrastructure to support service-to-service calls.

## 🔍 Current State Analysis

### Current Architecture

1. **Function Service Communication (✅ Working)**
   - `BaseFunction` has `call_service` property that provides syntax sugar: `self.call_service["service_name"].method()`
   - `TaskContext` contains `service_qds` (service queue descriptors) for making service calls
   - `TaskContext` has `response_qd` for receiving service responses
   - Service calls are managed through `ServiceManager` and `ServiceCallProxy`

2. **Service Architecture (⚠️ Limited)**
   - `BaseService` defines the service interface with `setup()`, `cleanup()`, `start()`, `stop()` methods
   - `BaseServiceTask` manages service lifecycle and request handling
   - `ServiceContext` contains context for service execution but lacks service call capabilities
   - Services currently access other services through awkward workarounds (see `MemoryService._get_kv_service()`)

### Current Limitations

1. **ServiceContext Missing Service Communication Infrastructure**
   ```python
   # ServiceContext currently has:
   self._request_queue_descriptor  # For receiving requests
   self._service_response_queue_descriptors  # For response queues (incomplete)
   
   # But lacks:
   # - service_qds: Service request queue descriptors for calling other services  
   # - service_manager: For managing service calls
   # - call_service property: Syntax sugar for service calls
   ```

2. **Incomplete Service Response Queue Management**
   - `ServiceContext` collects service response queues from execution graph
   - But it only collects from `execution_graph.nodes` (transformation nodes), not service nodes
   - Services need access to **all** service response queues, including from other services

3. **Missing Service Manager in ServiceContext**
   - `BaseServiceTask` cannot easily call other services
   - Current workaround in `MemoryService` uses `ctx.service_manager.get_service_proxy()` but this is inconsistent

## 🎯 Proposed Solution

### Phase 1: Extend ServiceContext with Service Communication

1. **Add Service Queue Descriptors to ServiceContext**
   ```python
   # In ServiceContext.__init__():
   # Add service request queue descriptors (similar to TaskContext)
   self.service_qds: Dict[str, 'BaseQueueDescriptor'] = {}
   if execution_graph:
       for service_name, service_node in execution_graph.service_nodes.items():
           if service_node.service_qd:
               self.service_qds[service_node.service_name] = service_node.service_qd
   ```

2. **Complete Service Response Queue Collection**
   ```python
   # In ServiceContext.__init__():
   # Current: only collects from execution_graph.nodes (transformation nodes)
   # Need: collect from BOTH transformation nodes AND service nodes
   if execution_graph:
       # Existing: transformation node response queues
       for node_name, node in execution_graph.nodes.items():
           if node.service_response_qd:
               self._service_response_queue_descriptors[node_name] = node.service_response_qd
       
       # NEW: service node response queues (for service-to-service calls)
       for service_name, service_node in execution_graph.service_nodes.items():
           if service_node.service_response_qd:  # Assuming services also have response queues
               self._service_response_queue_descriptors[service_name] = service_node.service_response_qd
   ```

3. **Add ServiceManager to ServiceContext**
   ```python
   # In ServiceContext:
   @property
   def service_manager(self) -> 'ServiceManager':
       if self._service_manager is None:
           from sage.kernel.runtime.service.service_caller import ServiceManager
           self._service_manager = ServiceManager(self, logger=self.logger)
       return self._service_manager
   ```

### Phase 2: Add Service Call Syntax Sugar to BaseService

1. **Add call_service Property to BaseService**
   ```python
   # In BaseService class:
   @property
   def call_service(self):
       """
       Service call syntax sugar for services
       Usage: self.call_service["other_service"].method_name(*args)
       """
       if self.ctx is None:
           raise RuntimeError("Service context not initialized. Cannot access services.")
       
       if not hasattr(self, '_call_service_proxy') or self._call_service_proxy is None:
           # Implementation similar to BaseFunction.call_service
           # ... (detailed implementation)
       
       return self._call_service_proxy
   ```

### Phase 3: Update ExecutionGraph Service Response Queue Generation

1. **Ensure Service Nodes Have Response Queues**
   ```python
   # In ExecutionGraph service node creation:
   # Make sure each service node has a service_response_qd for receiving responses
   # when it makes calls to other services
   ```

2. **Update Service Response Queue Distribution**
   ```python
   # In ExecutionGraph.generate_runtime_contexts():
   # Ensure ServiceContext gets ALL service response queues (from both transform nodes and service nodes)
   ```

## 🧪 Implementation Strategy

### Step 1: Extend ServiceContext
- [ ] Add `service_qds` mapping for service request queues
- [ ] Complete service response queue collection (include service nodes)
- [ ] Add `service_manager` property to ServiceContext
- [ ] Update ServiceContext initialization in ExecutionGraph

### Step 2: Extend BaseService  
- [ ] Add `call_service` property with syntax sugar
- [ ] Add `call_service_async` property for async calls
- [ ] Implement service call proxy similar to BaseFunction

### Step 3: Update ExecutionGraph
- [ ] Ensure service nodes have response queues
- [ ] Update service response queue collection to include service nodes
- [ ] Verify queue descriptor distribution to ServiceContext

### Step 4: Update Service Implementations
- [ ] Refactor `MemoryService` to use new `call_service` syntax
- [ ] Update other service implementations as needed
- [ ] Remove workaround code

## 📊 Expected Benefits

1. **Consistent Service Communication**
   - Services can call other services using the same syntax as functions
   - `self.call_service["kv_service"].put("key", "value")`

2. **Clean Architecture**
   - Remove workaround code in services
   - Unified service communication pattern

3. **Better Service Composition**
   - Enable complex service orchestration (like MemoryService coordinating KV+VDB+Graph)
   - Support for microservice patterns

4. **Maintainability**
   - Same service call infrastructure for both functions and services
   - Easier to add new service-to-service communications

## 🧪 Testing Strategy

1. **Unit Tests**
   - Test ServiceContext service queue descriptor collection
   - Test BaseService call_service property functionality  
   - Test service-to-service call routing

2. **Integration Tests**
   - Test MemoryService calling KVService and VDBService
   - Test service call error handling and timeouts
   - Test service call performance

3. **End-to-End Tests**
   - Test complex service orchestration scenarios
   - Verify service call reliability under load

## 📝 Implementation Notes

### Code Files to Modify

1. **ServiceContext (`/packages/sage-kernel/src/sage/kernel/runtime/service_context.py`)**
   - Add service_qds collection
   - Complete service response queue collection
   - Add service_manager property

2. **BaseService (`/packages/sage-kernel/src/sage/core/api/service/base_service.py`)**
   - Add call_service property
   - Add call_service_async property

3. **ExecutionGraph (`/packages/sage-kernel/src/sage/kernel/jobmanager/execution_graph/execution_graph.py`)**
   - Update service response queue collection logic
   - Ensure service nodes have response queues

4. **Service Implementations**
   - Refactor MemoryService to use new call_service syntax
   - Update other services as needed

### Backward Compatibility

- Existing service call mechanisms should continue working
- Gradually migrate services to new call_service syntax
- Maintain existing service APIs

---

**Priority**: High
**Complexity**: Medium  
**Impact**: High (enables proper microservice architecture)
**Dependencies**: None (uses existing service communication infrastructure)
