# Issue: Design and Implement CoMap Function for Multi-Stream Processing

## 📋 Overview
We need to design and implement a CoMap (Co-processing Map) function that enables parallel processing of multiple input streams in ConnectedStreams, where each input stream is processed independently rather than being merged into a single input.

## 🎯 Problem Statement
Currently, ConnectedStreams merges all upstream transformations into a single input (index 0) for processing. However, there are scenarios where we need to:
- Process multiple streams independently with different logic for each stream
- Maintain stream boundaries while applying coordinated transformations
- Enable more complex multi-stream operations like joins, unions, and synchronized processing

## 🔧 Proposed Design

### 1. CoMap Function Interface
```python
class BaseCoMapFunction(BaseFunction):
    """Base class for CoMap functions that process multiple inputs separately"""
    
    @property 
    def is_comap(self) -> bool:
        return True
    
    @abstractmethod
    def map0(self, data: Any) -> Any:
        """Process data from input stream 0 (required)"""
        pass
    
    @abstractmethod
    def map1(self, data: Any) -> Any:
        """Process data from input stream 1 (required)"""
        pass
    
    def map2(self, data: Any) -> Any:
        """Process data from input stream 2 (optional)"""
        raise NotImplementedError(f"map2 not implemented for {self.__class__.__name__}")
    
    def map3(self, data: Any) -> Any:
        """Process data from input stream 3 (optional)"""
        raise NotImplementedError(f"map3 not implemented for {self.__class__.__name__}")
    
    # Can add more mapN methods as needed...
```

### 2. CoMap Transformation
```python
class CoMapTransformation(BaseTransformation):
    """Transformation that applies CoMap functions to ConnectedStreams"""
    
    def __init__(self, env: 'BaseEnvironment', function: Type[BaseCoMapFunction], *args, **kwargs):
        super().__init__(env, function, *args, **kwargs)
        self.operator_class = CoMapOperator
        
        # Validate that function is a CoMap function
        if not hasattr(function, 'is_comap') or not function.is_comap:
            raise ValueError(f"Function {function.__name__} is not a CoMap function")
```

### 3. CoMap Operator
```python
class CoMapOperator(BaseOperator):
    """Operator that handles multi-input processing for CoMap functions"""
    
    def process(self, raw_data: Any = None, input_index: int = 0) -> Any:
        """
        Process data using the CoMap function with input index information.
        The operator receives a packet, extracts the input_index, and directly
        calls the appropriate mapN method on the function.
        """
        if raw_data is None:
            return None
        
        # Route directly to the appropriate mapN method based on input_index
        method_name = f"map{input_index}"
        if hasattr(self.function, method_name):
            method = getattr(self.function, method_name)
            return method(raw_data)
        else:
            raise NotImplementedError(f"Method {method_name} not implemented for {self.function.__class__.__name__}")
```

### 4. ConnectedStreams Enhancement
```python
class ConnectedStreams:
    # ... existing code ...
    
    def comap(self, function: Union[Type[BaseCoMapFunction], callable], *args, **kwargs) -> 'DataStream':
        """
        Apply a CoMap function that processes each connected stream separately
        
        Args:
            function: CoMap function class that implements map0, map1, ..., mapN methods
            
        Returns:
            DataStream: Result stream from coordinated processing
        """
        if callable(function) and not isinstance(function, type):
            # Lambda functions need special wrapper - not implemented yet
            raise NotImplementedError("Lambda functions not supported for comap operations")
        
        tr = CoMapTransformation(self._environment, function, *args, **kwargs)
        return self._apply(tr)
```

## 📝 Implementation Tasks

### Phase 1: Core Infrastructure
- [ ] Create `BaseCoMapFunction` abstract class with mapN method interface (no declare_inputs needed)
- [ ] Implement `CoMapTransformation` class
- [ ] Implement `CoMapOperator` class with direct mapN method routing in process()
- [ ] Update packet processing to extract input_index and route to CoMapOperator.process()
- [ ] Update `ConnectedStreams._apply()` logic to handle CoMap operations

### Phase 2: API Integration
- [ ] Add `comap()` method to `ConnectedStreams` class
- [ ] Update transformation detection logic in `_apply()`
- [ ] Ensure proper input index routing from packet directly to CoMapOperator.process()
- [ ] Add validation for required map0 and map1 methods in CoMapOperator
- [ ] Add error handling for missing mapN methods in operator routing logic

### Phase 3: Examples and Testing
- [ ] Create example CoMap functions using mapN pattern (join, synchronized processing)
- [ ] Write comprehensive test cases for mapN method dispatch
- [ ] Create documentation and usage examples
- [ ] Test error cases (missing map methods, wrong signatures)

## 🌟 Use Cases

### Example 1: Stream Synchronization
```python
class SyncProcessor(BaseCoMapFunction):
    def __init__(self):
        super().__init__()
        self.buffers = {}  # Buffer for each input stream
    
    def map0(self, data):
        """Process sensor data from stream 0"""
        self.buffers[0] = data
        return self._try_sync()
    
    def map1(self, data):
        """Process weather data from stream 1"""
        self.buffers[1] = data
        return self._try_sync()
    
    def _try_sync(self):
        """Try to synchronize data from all streams"""
        # Only emit when all streams have data
        if len(self.buffers) == 2:  # Assuming 2 input streams
            result = {
                'sensor': self.buffers[0],
                'weather': self.buffers[1],
                'timestamp': time.time()
            }
            self.buffers.clear()
            return result
        return None

# Usage
sensor_stream = env.from_source(SensorSource)
weather_stream = env.from_source(WeatherSource)

synchronized = (sensor_stream
    .connect(weather_stream)
    .comap(SyncProcessor)
    .filter(lambda x: x is not None)  # Filter out None values
    .print("Synchronized Data"))
```

### Example 2: Type-Specific Processing
```python
class TypeSpecificProcessor(BaseCoMapFunction):
    def map0(self, data):
        """Process temperature data from stream 0"""
        return f"Temperature: {data}°C"
    
    def map1(self, data):
        """Process humidity data from stream 1"""
        return f"Humidity: {data}%"
    
    def map2(self, data):
        """Process pressure data from stream 2 (optional)"""
        return f"Pressure: {data} hPa"

# Usage
result = (temp_stream
    .connect(humidity_stream)
    .connect(pressure_stream)
    .comap(TypeSpecificProcessor)
    .print("Processed"))
```

## 🔍 Benefits
1. **Fine-grained Control**: Process each input stream with specific logic using dedicated mapN methods
2. **Clear Interface**: Explicit map0, map1, ..., mapN methods make stream handling intentions obvious
3. **Stream Coordination**: Enable complex multi-stream operations with proper isolation
4. **Performance**: Avoid unnecessary merging when streams need separate processing
5. **Extensibility**: Foundation for advanced operations like windowed joins
6. **Type Safety**: Maintain type information for each input stream
7. **Debugging**: Easy to trace which mapN method handles each stream

## 📋 File Changes Required
- `sage_core/function/base_comap_function.py` (new)
- `sage_core/transformation/comap_transformation.py` (new)
- `sage_core/operator/comap_operator.py` (new)
- connected_streams.py (enhancement)
- lambda_function.py (add comap lambda support)
- `sage_examples/comap_example.py` (new)

## 🎯 Acceptance Criteria
- [ ] CoMap functions can process multiple input streams independently using mapN methods
- [ ] Input index information is correctly propagated through the pipeline to call appropriate mapN method
- [ ] ConnectedStreams.comap() provides intuitive API with clear method-based interface
- [ ] CoMap functions support at least map0 and map1 (required), with optional map2, map3, etc.
- [ ] Performance impact is minimal for existing single-input operations
- [ ] Comprehensive examples demonstrate practical use cases with mapN pattern
- [ ] Error handling for missing mapN methods is robust and informative

## 🔗 Related Issues
- Enhances the ConnectedStreams functionality introduced in the current PR
- Builds upon the multi-input transformation architecture
- Enables future windowing and join operations