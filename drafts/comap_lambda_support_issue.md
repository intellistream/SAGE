# Issue: Enhanced CoMap Function Interface with Lambda and Callable Support

## 📋 Overview
We need to enhance the CoMap function interface to support lambda functions and direct callables for simpler use cases, providing multiple convenient ways to define CoMap operations without requiring users to create full class implementations.

## 🎯 Problem Statement
Currently, CoMap functions require users to:
- Define a class that inherits from `BaseCoMapFunction`
- Implement required `map0`, `map1`, and optional `mapN` methods
- Handle constructor parameters manually

This creates barriers for simple use cases where users just want to apply different lambda functions to different input streams without the overhead of class definition.

## 🔧 Proposed Enhanced Interface

### 1. Lambda Function List Support
```python
# Support passing a list of functions
result = (stream1
    .connect(stream2)
    .connect(stream3)
    .comap([
        lambda x: f"Temperature: {x}°C",    # map0
        lambda x: f"Humidity: {x}%",        # map1
        lambda x: f"Pressure: {x} hPa"      # map2
    ])
    .print("Sensor Data"))
```

### 2. Direct Function Arguments Support
```python
# Support passing functions as separate arguments
def process_temp(data):
    return f"🌡️ {data['value']}°C"

def process_humidity(data):
    return f"💧 {data['value']}%"

def process_pressure(data):
    return f"🔘 {data['value']} hPa"

result = (stream1
    .connect(stream2)
    .connect(stream3)
    .comap(process_temp, process_humidity, process_pressure)
    .print("Processed"))
```

### 3. Mixed Function Types Support
```python
# Support mixing lambda and named functions
result = (stream1
    .connect(stream2)
    .comap(
        lambda x: x * 2,           # map0
        process_humidity           # map1
    )
    .print("Mixed Processing"))
```

### 4. Backward Compatibility
```python
# Existing class-based approach still works
class MyCoMapFunction(BaseCoMapFunction):
    def __init__(self, multiplier=2):
        super().__init__()
        self.multiplier = multiplier
    
    def map0(self, data):
        return data * self.multiplier
    
    def map1(self, data):
        return data + 10

result = (stream1
    .connect(stream2)
    .comap(MyCoMapFunction, multiplier=3)  # Constructor args still supported
    .print("Class-based"))
```

## 🔧 Implementation Design

### 1. Enhanced CoMap Interface Detection
```python
def comap(self, function: Union[Type[BaseFunction], callable, List[callable]], *args, **kwargs) -> 'DataStream':
    """
    Enhanced CoMap with multiple input formats:
    1. BaseCoMapFunction class (existing)
    2. List of callables [func0, func1, func2, ...]
    3. Individual callables as arguments (func0, func1, func2, ...)
    """
    
    # Case 1: List of functions
    if isinstance(function, list):
        return self._comap_from_function_list(function)
    
    # Case 2: Multiple function arguments (detect if args contain callables)
    elif args and all(callable(arg) for arg in args):
        function_list = [function] + list(args)
        return self._comap_from_function_list(function_list)
    
    # Case 3: Single callable (convert to single-item list)
    elif callable(function) and not isinstance(function, type):
        function_list = [function]
        return self._comap_from_function_list(function_list)
    
    # Case 4: Existing class-based approach
    else:
        return self._comap_from_class(function, *args, **kwargs)
```

### 2. Dynamic CoMap Class Generation
```python
def _comap_from_function_list(self, function_list: List[callable]) -> 'DataStream':
    """Create a dynamic CoMap class from a list of functions"""
    
    # Validate function count matches input streams
    input_stream_count = len(self.transformations)
    if len(function_list) != input_stream_count:
        raise ValueError(
            f"Number of functions ({len(function_list)}) must match "
            f"number of input streams ({input_stream_count})"
        )
    
    # Create dynamic CoMap class
    class DynamicCoMapFunction(BaseCoMapFunction):
        def __init__(self):
            super().__init__()
            self.functions = function_list
        
        @property
        def is_comap(self) -> bool:
            return True
        
        def execute(self, data: Any) -> Any:
            # Still not implemented - use mapN methods
            raise NotImplementedError("Use mapN methods for CoMap functions")
    
    # Dynamically add mapN methods
    for i, func in enumerate(function_list):
        method_name = f"map{i}"
        # Create method that calls the provided function
        def create_map_method(function):
            def map_method(self, data):
                return function(data)
            return map_method
        
        setattr(DynamicCoMapFunction, method_name, create_map_method(func))
    
    # Create transformation with dynamic class
    tr = CoMapTransformation(self._environment, DynamicCoMapFunction)
    tr.validate_input_streams(input_stream_count)
    return self._apply(tr)
```

### 3. Function Validation and Wrapping
```python
class LambdaCoMapWrapper:
    """Wrapper for lambda-based CoMap functions"""
    
    def __init__(self, function_list: List[callable]):
        self.function_list = function_list
        self._validate_functions()
    
    def _validate_functions(self):
        """Validate that all items are callable"""
        for i, func in enumerate(self.function_list):
            if not callable(func):
                raise ValueError(f"Item at index {i} is not callable: {type(func)}")
    
    @property
    def is_comap(self) -> bool:
        return True
    
    def get_map_method(self, index: int) -> callable:
        """Get the function for the specified input index"""
        if index >= len(self.function_list):
            raise NotImplementedError(f"map{index} not implemented - only {len(self.function_list)} functions provided")
        return self.function_list[index]
```

## 🌟 Usage Examples

### Example 1: Simple Data Formatting
```python
# Before (class-based)
class SimpleFormatter(BaseCoMapFunction):
    def map0(self, data):
        return f"Stream 0: {data}"
    def map1(self, data):
        return f"Stream 1: {data}"

result = streams.comap(SimpleFormatter)

# After (lambda-based)
result = streams.comap([
    lambda x: f"Stream 0: {x}",
    lambda x: f"Stream 1: {x}"
])
```

### Example 2: Mathematical Operations
```python
# Different operations on different streams
result = (numeric_stream1
    .connect(numeric_stream2)
    .connect(numeric_stream3)
    .comap(
        lambda x: x * 2,        # Double first stream
        lambda x: x + 10,       # Add 10 to second stream
        lambda x: x ** 2        # Square third stream
    ))
```

### Example 3: Type-Specific Processing
```python
def format_temperature(data):
    return f"🌡️ {data['value']}°C ({'Hot' if data['value'] > 30 else 'Normal'})"

def format_humidity(data):
    return f"💧 {data['value']}% ({'High' if data['value'] > 80 else 'Normal'})"

result = (temp_stream
    .connect(humidity_stream)
    .comap(format_temperature, format_humidity)
    .print("Formatted Sensors"))
```

### Example 4: Error Handling with Lambdas
```python
result = streams.comap([
    lambda x: x if x > 0 else 0,                    # Clamp negative values
    lambda x: round(x, 2) if isinstance(x, float) else x,  # Round floats
    lambda x: str(x).upper() if isinstance(x, str) else x  # Uppercase strings
])
```

## 📝 Implementation Tasks

### Phase 1: Core Lambda Support
- [ ] Extend `comap()` method signature to accept `List[callable]`
- [ ] Implement dynamic CoMap class generation
- [ ] Add function validation and error handling
- [ ] Update `CoMapTransformation` to handle lambda-based functions

### Phase 2: Multiple Argument Support
- [ ] Add detection for multiple callable arguments
- [ ] Implement argument parsing and validation
- [ ] Add support for mixed function types
- [ ] Ensure proper error messages for argument mismatches

### Phase 3: Enhanced Validation
- [ ] Validate function count matches input stream count
- [ ] Add runtime validation for lambda function signatures
- [ ] Implement helpful error messages for common mistakes
- [ ] Add debugging support for lambda-based CoMap functions

### Phase 4: Documentation and Examples
- [ ] Update `comap()` method documentation with all supported formats
- [ ] Create comprehensive examples for each usage pattern
- [ ] Add migration guide from class-based to lambda-based approach
- [ ] Update existing examples to show lambda alternatives

## 🔍 Benefits

### 1. **Developer Experience**
- **Reduced Boilerplate**: No need to define classes for simple operations
- **Inline Definition**: Functions defined directly at usage point
- **Familiar Syntax**: Similar to other functional programming patterns

### 2. **Flexibility**
- **Multiple Input Formats**: List, arguments, or individual functions
- **Mixed Types**: Combine lambda and named functions as needed
- **Progressive Enhancement**: Start simple, move to classes when needed

### 3. **Maintainability**
- **Reduced Code**: Less code for simple transformations
- **Clear Intent**: Function purpose obvious at call site
- **Easy Testing**: Individual functions can be tested independently

### 4. **Backward Compatibility**
- **Zero Breaking Changes**: All existing code continues to work
- **Gradual Migration**: Can adopt lambda syntax incrementally
- **Performance**: No overhead for existing class-based approach

## ⚠️ Limitations and Trade-offs

### 1. **Constructor Arguments**
- Lambda-based approach cannot pass constructor arguments to user-defined classes
- State sharing between mapN methods requires class-based approach
- Complex initialization logic needs class constructors

### 2. **Type Safety**
- Lambda functions have less explicit type information
- Runtime errors may be less clear than class-based validation
- IDE support may be limited for lambda-generated methods

### 3. **Debugging**
- Lambda functions harder to debug than named methods
- Stack traces may be less informative
- Profiling individual mapN methods more difficult

## 🎯 Acceptance Criteria

- [ ] Support `comap([func0, func1, func2])` syntax
- [ ] Support `comap(func0, func1, func2)` syntax  
- [ ] Support single callable `comap(lambda x: x*2)` for single-stream case
- [ ] Maintain full backward compatibility with class-based approach
- [ ] Provide clear error messages for function count mismatches
- [ ] Performance impact minimal compared to class-based approach
- [ ] Comprehensive documentation with examples for all syntax forms
- [ ] Proper validation and error handling for edge cases

## 🔗 Related Issues
- Builds upon the CoMap Function implementation
- Enhances developer experience for ConnectedStreams
- Provides foundation for more functional programming patterns in SAGE
