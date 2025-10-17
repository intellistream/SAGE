# Service Integration Tutorials

Learn how to integrate SAGE services and build service-oriented applications.

## Overview

This directory contains tutorials for SAGE's service-oriented features:
- **Pipeline as Service**: Expose SAGE pipelines as web services
- **SAGE DB**: High-performance vector database service
- **SAGE Flow**: Stream processing service
- **Embedding Service**: Text embedding as a service

## Examples

### Embedding Service

**`embedding_service_demo.py`** - Basic embedding service
```bash
python examples/tutorials/service/embedding_service_demo.py
```

Learn how to:
- Create an embedding service
- Handle batch embedding requests
- Integrate with pipelines

---

### Pipeline as Service

Transform SAGE pipelines into REST/gRPC services.

#### **`hello_pipeline_as_service.py`** - Basic service
```bash
python examples/tutorials/service/pipeline_as_service/hello_pipeline_as_service.py
```

Simple pipeline exposed as a service.

#### **`qa_pipeline_as_service.py`** - QA service
```bash
python examples/tutorials/service/pipeline_as_service/qa_pipeline_as_service.py
```

Question-answering pipeline as a service.

**Requirements**: API keys in `.env`

#### **`multi_client_pipeline_as_service.py`** - Multi-client
```bash
python examples/tutorials/service/pipeline_as_service/multi_client_pipeline_as_service.py
```

Handle multiple concurrent clients.

#### **`async_client_pipeline_as_service.py`** - Async client
```bash
python examples/tutorials/service/pipeline_as_service/async_client_pipeline_as_service.py
```

Asynchronous client implementation.

#### **`pipeline_bridge.py`** - Service bridge
```bash
python examples/tutorials/service/pipeline_as_service/pipeline_bridge.py
```

Bridge between different services.

See: `pipeline_as_service/README.md` for details

---

### SAGE DB Service

High-performance vector database integration.

#### **`hello_sage_db_service.py`** - Service mode
```bash
python examples/tutorials/service/sage_db/hello_sage_db_service.py
```

Run SAGE DB as a service.

#### **`hello_sage_db_app.py`** - Application mode
```bash
python examples/tutorials/service/sage_db/hello_sage_db_app.py
```

Use SAGE DB in your application.

See: `sage_db/README.md` for details

---

### SAGE Flow Service

Stream processing and vector flow management.

#### **`hello_sage_flow_service.py`** - Service mode
```bash
python examples/tutorials/service/sage_flow/hello_sage_flow_service.py
```

Run SAGE Flow as a service.

#### **`hello_sage_flow_app.py`** - Application mode
```bash
python examples/tutorials/service/sage_flow/hello_sage_flow_app.py
```

Use SAGE Flow in your application.

See: `sage_flow/README.md` for details

---

## Architecture Patterns

### Pattern 1: Microservices
Break your AI application into independent services:
- Embedding Service
- Retrieval Service
- Generation Service

### Pattern 2: Pipeline as Service
Expose entire pipelines as APIs:
- REST endpoints
- gRPC services
- WebSocket streaming

### Pattern 3: Hybrid
Combine embedded and service modes:
- Use services for heavy operations
- Embed lightweight components

## Configuration

Service examples typically use configuration files in `examples/config/`:
- `config_source.yaml` - Data source configuration
- `config.yaml` - General pipeline configuration

## Next Steps

**After completing these tutorials:**

1. **Build Production Services**
   - Add authentication
   - Implement load balancing
   - Add monitoring and logging

2. **Explore Middleware**
   - `packages/sage-middleware/` - Service infrastructure
   - SAGE DB source code
   - SAGE Flow source code

3. **Advanced Integration**
   - Distributed services with Ray
   - Service mesh patterns
   - Cloud deployment

## Resources

- **Middleware Package**: `packages/sage-middleware/`
- **SAGE DB**: `packages/sage-middleware/src/sage/middleware/components/sage_db/`
- **SAGE Flow**: `packages/sage-middleware/src/sage/middleware/components/sage_flow/`
- **Service API**: `examples/tutorials/service-api/`

## Tips

- Start services before running clients
- Check port availability (default: 8000, 50051)
- Use `Ctrl+C` to stop services gracefully
- Monitor logs for debugging
