# PR: Implement CoMap Function for Multi-Stream Processing

## 📋 Overview
This PR implements the CoMap (Co-processing Map) function feature that enables parallel processing of multiple input streams in ConnectedStreams, where each input stream is processed independently using dedicated `mapN` methods rather than being merged into a single processing function.

## 🎯 Problem Statement
Previously, ConnectedStreams could only merge all upstream transformations into a single input (index 0) for processing. This limitation prevented scenarios where:
- Different input streams require type-specific processing logic
- Stream boundaries need to be maintained during transformation
- Complex multi-stream operations like joins and synchronized processing are needed

## 🔧 Solution: CoMap Function Architecture

### Core Design Principles
1. **Stream Independence**: Each input stream is processed by its dedicated `mapN` method
2. **Type Safety**: Each `mapN` method can assume specific data formats
3. **Method-Based Routing**: Operator-level routing based on `input_index` to appropriate `mapN` methods
4. **Validation Framework**: Comprehensive validation at multiple layers

## 📁 New Files Added

### Core Infrastructure
- **`sage_core/function/comap_function.py`** - Base CoMap function interface
- **`sage_core/transformation/comap_transformation.py`** - CoMap transformation layer
- **`sage_core/operator/comap_operator.py`** - CoMap operator with intelligent routing
- **`sage_examples/comap_function_example.py`** - Comprehensive usage example

## 🔧 Key Implementation Details

### 1. BaseCoMapFunction Interface
```python
class BaseCoMapFunction(BaseFunction):
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
```

### 2. Intelligent Operator Routing
```python
class CoMapOperator(BaseOperator):
    def process(self, raw_data: Any = None, input_index: int = 0) -> Any:
        # Route directly to the appropriate mapN method based on input_index
        method_name = f"map{input_index}"
        if hasattr(self.function, method_name):
            method = getattr(self.function, method_name)
            return method(raw_data)
        else:
            raise NotImplementedError(f"Method {method_name} not implemented")
```

### 3. Enhanced ConnectedStreams API
```python
def comap(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> 'DataStream':
    """Apply a CoMap function that processes each connected stream separately"""
    # Validation and transformation creation
    tr = CoMapTransformation(self._environment, function, *args, **kwargs)
    tr.validate_input_streams(len(self.transformations))
    return self._apply(tr)
```

## ✨ Key Features

### 1. **Multi-Layer Validation**
- **Function Level**: Validates `is_comap=True` and required `map0`/`map1` methods
- **Transformation Level**: Checks input stream count against available `mapN` methods
- **Operator Level**: Runtime validation and method existence checking

### 2. **Smart Method Detection**
- Automatically detects supported input stream count
- Provides clear error messages for missing methods
- Supports optional `map2`, `map3`, `map4` methods for extensibility

### 3. **Error Handling & Debugging**
- Comprehensive error messages with actionable guidance
- Debug logging for method routing
- Clear distinction between missing methods and runtime errors

### 4. **Backward Compatibility**
- No changes to existing ConnectedStreams merge behavior
- CoMap functions are opt-in via `is_comap=True` property
- Existing transformation pipeline remains unchanged

## 🌟 Usage Examples

### Multi-Sensor Data Processing
```python
class SensorDataProcessor(BaseCoMapFunction):
    def map0(self, data):
        """Process temperature data"""
        temp_value = data['value']
        status = "🔥 HIGH" if temp_value > 30.0 else "✅ Normal"
        return {'stream': 'temperature', 'value': f"{temp_value}°C", 'status': status}
    
    def map1(self, data):
        """Process humidity data"""
        humidity_value = data['value']
        status = "💧 HIGH" if humidity_value > 80.0 else "✅ Normal"
        return {'stream': 'humidity', 'value': f"{humidity_value}%", 'status': status}

# Usage
result = (temp_stream
    .connect(humidity_stream)
    .comap(SensorDataProcessor)
    .print("Sensor Results"))
```

### Type-Specific Formatting
```python
class TypeSpecificProcessor(BaseCoMapFunction):
    def map0(self, data):
        return f"🌡️ Temperature: {data['value']}°C"
    
    def map1(self, data):
        return f"💧 Humidity: {data['value']}%"
```

## 📊 Technical Improvements

### Performance Benefits
- **No Unnecessary Merging**: Streams processed independently without data copying
- **Direct Method Dispatch**: O(1) method lookup via `getattr()`
- **Minimal Overhead**: Only additional validation at initialization time

### Architecture Benefits
- **Clear Separation of Concerns**: Each `mapN` method handles one stream type
- **Type Safety**: Stream-specific processing with expected data formats
- **Extensibility**: Easy to add more input streams by implementing additional `mapN` methods

## 🧪 Testing & Validation

### Comprehensive Example Application
The `comap_function_example.py` demonstrates:
- **Multi-sensor simulation**: Temperature, humidity, and pressure sensors
- **Real-world processing**: Alert detection and status monitoring
- **Two CoMap implementations**: Complex processing and simple formatting
- **Practical usage patterns**: Different sensor frequencies and data types

### Error Scenarios Covered
- Missing required `map0`/`map1` methods
- Insufficient input streams (< 2 required)
- Excess input streams without corresponding `mapN` methods
- Invalid function types (non-CoMap functions)

## 🔄 Migration Impact

### For Existing Code
- **Zero Breaking Changes**: All existing ConnectedStreams functionality preserved
- **Opt-in Feature**: CoMap only activated when `is_comap=True`
- **API Consistency**: `comap()` method follows same patterns as `map()` and `sink()`

### For New Development
- **Enhanced Capabilities**: Multi-stream processing with type safety
- **Clear Documentation**: Comprehensive examples and error messages
- **Gradual Adoption**: Can mix regular and CoMap operations as needed

## 📋 Files Modified

### Core API Enhancement
- **`sage_core/api/connected_streams.py`**: Added `comap()` method with full documentation

### Function Framework
- **`sage_core/function/base_function.py`**: Removed obsolete documentation comments

### New Architecture Components
- **`sage_core/function/comap_function.py`**: Complete CoMap function framework
- **`sage_core/transformation/comap_transformation.py`**: Multi-input transformation handling
- **`sage_core/operator/comap_operator.py`**: Intelligent method routing operator

### Documentation & Examples
- **`sage_examples/comap_function_example.py`**: Comprehensive real-world example

## 🎯 Future Enhancements Enabled

This CoMap foundation enables future advanced features:
- **Windowed Joins**: Time-based stream synchronization
- **Stream Unions**: Coordinated processing of related streams
- **State Sharing**: Cross-stream state management
- **Complex Event Processing**: Pattern detection across multiple streams

## ✅ Acceptance Criteria Met

- ✅ CoMap functions process multiple input streams independently using `mapN` methods
- ✅ Input index information correctly propagated through pipeline to appropriate `mapN` method
- ✅ `ConnectedStreams.comap()` provides intuitive API with clear method-based interface
- ✅ CoMap functions support required `map0` and `map1`, with optional `map2`, `map3`, etc.
- ✅ Performance impact minimal for existing single-input operations
- ✅ Comprehensive examples demonstrate practical use cases with `mapN` pattern
- ✅ Error handling for missing `mapN` methods is robust and informative

## 🔗 Related Work

This PR enhances the ConnectedStreams functionality and builds upon the multi-input transformation architecture, providing the foundation for future windowing and join operations while maintaining full backward compatibility with existing code.
