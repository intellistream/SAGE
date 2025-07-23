# GitHub Copilot Instructions for SAGE Framework

## Project Overview

SAGE is a **dataflow-native reasoning framework** built to support modular, controllable, and transparent workflows over Large Language Models (LLMs). The framework models reasoning workflows as directed acyclic graphs (DAGs) composed of typed operators, addressing problems like hard-coded orchestration logic, opaque execution paths, and limited runtime control in existing LLM-augmented systems.

### Key Technologies
- **Python 3.11+**: Primary development language with strict type annotations
- **C++17/20**: Required for sage_flow runtime core (Modern C++ features)
- **FastAPI**: Backend API server for web interface
- **Angular 16**: Frontend dashboard for DAG visualization
- **Ray**: Distributed computing support for remote execution
- **Docker**: Containerized deployment support

## Architecture Overview

SAGE follows a **modular architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    SAGE Framework                          │
├─────────────────┬─────────────────┬─────────────────────────┤
│   sage_core     │  sage_runtime   │      sage_flow          │
│   (API/Ops)     │   (Execution)   │   (Data Processing)     │
├─────────────────┼─────────────────┼─────────────────────────┤
│  sage_memory    │   sage_libs     │    sage_plugins         │
│  (Vector DB)    │  (RAG/Agents)   │   (Extensions)          │
├─────────────────┼─────────────────┼─────────────────────────┤
│  sage_frontend  │ sage_jobmanager │     sage_utils          │
│  (Dashboard)    │  (Job Control)  │   (Utilities)           │
└─────────────────┴─────────────────┴─────────────────────────┘
```

### Module Responsibilities

1. **sage_core**: Core API and operator abstractions
   - `api/`: User-facing DataStream API for pipeline construction
   - `function/`: Base classes for user-defined functions (MapFunction, StatefulFunction)
   - `operator/`: Built-in operators for data transformation
   - `transformation/`: Pipeline transformation and compilation logic

2. **sage_runtime**: Execution engine and runtime management
   - `local/`: Local multi-threaded execution runtime
   - `remote/`: Distributed execution using Ray
   - `compiler.py`: Pipeline compilation and optimization
   - `mixed_dag.py`: Hybrid execution graph representation

3. **sage_flow**: Data processing framework with C++ runtime
   - **Note**: Runtime code MUST be written in C++17/20
   - Python interfaces only for SAGE framework integration
   - Handles data vectorization and multimodal processing
   - References `flow_old/` for design patterns (do NOT reuse code)

4. **sage_memory**: Vector database and search capabilities
   - Supports hybrid search (vector + keyword)
   - Environment configuration via `.env` files
   - Integration with various embedding models

5. **sage_libs**: RAG and agent implementations
   - `rag/`: Retrieval-Augmented Generation components
   - `agents/`: Multi-agent system implementations
   - `tools/`: External tool integrations

6. **sage_frontend**: Web-based dashboard and API server
   - `dashboard/`: Angular-based DAG visualization and monitoring
   - `sage_server/`: FastAPI backend for job management
   - Real-time pipeline monitoring and control

## Development Patterns

### 1. DataStream API Usage
```python
# Typical pipeline construction pattern
env = LocalEnvironment("pipeline_name")
env.set_memory(config={"collection_name": "memory_name"})

# Chain operators using fluent API
result = (env
    .from_source(FileSource, config["source"])
    .map(DenseRetriever, config["retriever"])
    .map(QAPromptor, config["promptor"])
    .map(OpenAIGenerator, config["generator"])
    .sink(TerminalSink, config["sink"])
)

# Submit and execute
env.submit()
env.run_streaming()
```

### 2. Function Implementation
```python
from sage_core.function.map_function import MapFunction
from typing import Any

class MyCustomFunction(MapFunction):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
    
    def map(self, data: Any) -> Any:
        # Process data
        return processed_data
```

### 3. Configuration Management
- Use YAML files in `config/` directory for pipeline configuration
- Environment variables via `.env` files (especially for API keys)
- Configuration loading via `sage_utils.config_loader.load_config()`

### 4. Logging and Monitoring
```python
from sage_utils.logging_utils import configure_logging
from sage_utils.custom_logger import CustomLogger

configure_logging(level=logging.INFO)
logger = CustomLogger(__name__)
```

## Critical Development Guidelines

### Code Quality Standards
1. **Type Annotations**: Use strict type hints throughout
2. **Error Handling**: Implement comprehensive exception handling
3. **Documentation**: Include docstrings for all public methods
4. **Testing**: Write tests in `sage_tests/` using pytest framework

### Architecture Constraints
1. **sage_flow**: Runtime code MUST be C++17/20, Python only for interfaces
2. **Memory Management**: Use proper resource cleanup in stateful functions
3. **Configuration**: Never hardcode API keys or paths
4. **Modularity**: Maintain clear boundaries between modules

### Performance Considerations
1. **Streaming**: Use streaming data processing where possible
2. **Parallel Execution**: Leverage both local threads and Ray for scalability
3. **Memory Efficiency**: Implement proper memory management in long-running pipelines
4. **Caching**: Use appropriate caching strategies for expensive operations

## Common Workflows

### Adding New Operators
1. Inherit from `MapFunction` or `StatefulFunction` in `sage_core/function/`
2. Implement required methods (`map()`, `setup()`, `cleanup()`)
3. Add configuration schema
4. Create examples in `sage_examples/`
5. Update documentation

### Pipeline Development
1. Create YAML configuration in `config/`
2. Implement pipeline logic using DataStream API
3. Add example in `sage_examples/`
4. Test with both LocalEnvironment and RemoteEnvironment
5. Add monitoring via dashboard

### Frontend Integration
1. Backend APIs in `sage_frontend/sage_server/routers/`
2. Frontend components in `sage_frontend/dashboard/src/app/`
3. Use TypeScript interfaces matching Python models
4. Implement real-time updates via WebSocket/polling

### Multi-Agent Systems
- Use agent classes from `sage_libs/agents/`
- Implement tool integrations in `sage_libs/tools/`
- Chain agents using standard DataStream API
- Add conversation memory and context management

## File Organization

### Configuration Files
- `config/*.yaml`: Pipeline configurations
- `.env`: Environment variables (never commit)
- `setup.py`: Package dependencies and metadata

### Examples and Tests
- `sage_examples/`: Working examples for different use cases
- `sage_tests/`: Test suites using pytest
- `playground/`: Experimental code and prototypes

### Documentation
- `docs/`: Architecture and design documentation
- `README.md`: Main project documentation
- Module-level READMEs in each package

## Integration Points

### External Services
- **OpenAI/Alibaba APIs**: Via `sage_libs/rag/generator.py`
- **Vector Databases**: Via `sage_memory/` components
- **Search APIs**: Via `sage_libs/tools/` integrations

### Monitoring and Management
- **Job Management**: Via `sage_jobmanager/` and dashboard
- **Performance Metrics**: Real-time monitoring in web dashboard
- **Resource Usage**: CPU, memory, and throughput tracking

## Best Practices for AI Assistance

1. **Understand Context**: Always consider the module boundaries and responsibilities
2. **Follow Patterns**: Use existing code patterns from `sage_examples/`
3. **Configuration-Driven**: Make components configurable rather than hardcoded
4. **Error Resilience**: Add proper error handling and recovery mechanisms
5. **Performance Aware**: Consider streaming, parallelism, and resource usage
6. **Documentation**: Maintain clear documentation for complex logic

When implementing new features or fixing bugs, always consider the impact on the entire dataflow pipeline and ensure compatibility with both local and distributed execution environments.
