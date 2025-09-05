# SAGE Flow Python Bindings

This directory contains Python bindings for the SAGE Flow C++ framework using pybind11.

## File Organization

```
src/python/
├── README.md                    # This file
├── datastream_bindings.cpp      # Main DataStream API bindings (PyDataStream, PyEnvironment)
└── operators/                   # Operator-specific bindings
    ├── terminal_sink_operator_bindings.cpp
    ├── file_sink_operator_bindings.cpp
    └── vector_store_sink_operator_bindings.cpp
```

## Module Structure

### Main Module: `sage_flow_datastream`

This is the primary Python module that provides:
- `PyDataStream`: Python interface for DataStream API
- `PyEnvironment`: Environment management
- `PyMultiModalMessage`: Message handling
- All operator bindings

**Usage in Python:**
```python
import sage_flow_datastream as sfd

# Create environment and datastream
env = sfd.PyEnvironment("test_pipeline")
ds = env.create_datastream()

# Build pipeline
result = (ds
    .from_source("input.txt")
    .map(lambda x: x.upper())
    .filter(lambda x: len(x) > 5)
    .sink(print)
)

# Execute
env.execute()
```

## Operator Bindings

Each operator has its own binding file in the `operators/` directory:

- **terminal_sink_operator_bindings.cpp**: Terminal output sink
- **file_sink_operator_bindings.cpp**: File output sink with various formats
- **vector_store_sink_operator_bindings.cpp**: Vector database sink

## Build Integration

All binding files are compiled into the `sage_flow_datastream` module via CMakeLists.txt:

```cmake
pybind11_add_module(sage_flow_datastream
  src/python/datastream_bindings.cpp
  src/python/operators/terminal_sink_operator_bindings.cpp
  src/python/operators/file_sink_operator_bindings.cpp
  src/python/operators/vector_store_sink_operator_bindings.cpp
)
```

## Development Notes

- All operator bindings are included in the main module
- Function signatures match the C++ API exactly
- Memory management handled automatically by pybind11
- Type conversions between Python and C++ are automatic for STL types
