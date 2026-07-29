# Pipeline-as-Service Demo

These examples show how to register an entire SAGE pipeline as a service while still leveraging the
same service invocation helpers for its internal stages. Each scenario adds a different client
pattern so you can see how pipelines and services compose in more realistic setups.

## What it demonstrates

- **Pipeline as a service** – The decision pipeline is registered as the `order_pipeline` service
  and can be invoked via `call_service`.
- **Asynchronous invocation** – Operators can use `self.call_service_async(...)` to overlap work and
  wait on a `Future`.
- **Service-to-service orchestration** – The pipeline calls supporting services (feature store, risk
  scoring) using the same helpers.
- **Cooperative shutdown** – Sending a `{"command": "shutdown"}` message tells the pipeline to stop
  after finishing in-flight work.

## Files

- `hello_pipeline_as_service.py` – Creates the service-backed decision pipeline plus a driver
  pipeline that submits orders and prints the returned decisions.
- `async_client_pipeline_as_service.py` – Uses `call_service_async` to submit a burst of requests
  concurrently and wait for futures to resolve.
- `multi_client_pipeline_as_service.py` – Spawns two driver pipelines (new vs returning users) that
  share the same pipeline service endpoint.
- `qa_pipeline_as_service.py` – Wraps the RAG QA pipeline as a service so an interactive terminal
  client waits for each answer before accepting the next question; exit by typing `bye bye` (or
  press `Ctrl+C` to interrupt).
- `pipeline_bridge.py` – Shared queue bridge used to pass requests between the driver pipelines and
  the service-backed pipeline.

## How to run

From the repository root you can run any scenario. For example:

```bash
python packages/sage-kernel/examples/advanced/pipeline_as_service/hello_pipeline_as_service.py
python packages/sage-kernel/examples/advanced/pipeline_as_service/async_client_pipeline_as_service.py
python packages/sage-kernel/examples/advanced/pipeline_as_service/multi_client_pipeline_as_service.py
python packages/sage-kernel/examples/advanced/pipeline_as_service/qa_pipeline_as_service.py
```

You should see log output from both the service-backed pipeline and the client pipelines, including
enrichment, scoring, service replies, and a shutdown acknowledgement once all work completes.

### Offline/mock QA runs (default)

The QA pipeline now uses **SageLLMGenerator** with mock backend by default, allowing it to run
completely offline without any external services:

```bash
# Default: uses mock backend (no external services required)
python packages/sage-kernel/examples/advanced/pipeline_as_service/qa_pipeline_as_service.py

# Explicitly use mock backend
SAGE_QA_GENERATOR=mock python packages/sage-kernel/examples/advanced/pipeline_as_service/qa_pipeline_as_service.py
```

The mock generator emits friendly placeholder replies so you can experience the request/response
flow without external dependencies.

### Using a real LLM

To use a real LLM backend, configure the following environment variables:

```bash
# Use SageLLM with auto-detected backend (cuda/ascend)
SAGE_QA_GENERATOR=sagellm \
SAGE_QA_BACKEND=auto \
SAGE_QA_MODEL_PATH=Qwen/Qwen2.5-7B-Instruct \
python packages/sage-kernel/examples/advanced/pipeline_as_service/qa_pipeline_as_service.py

# Additional configuration options
SAGE_QA_MAX_TOKENS=1024        # Maximum tokens to generate
SAGE_QA_TEMPERATURE=0.7        # Sampling temperature
SAGE_QA_TOP_P=0.95             # Nucleus sampling parameter
```

Supported `SAGE_QA_BACKEND` values:

- `mock` (default): No external services, returns placeholder responses
- `auto`: Auto-detect available hardware (cuda/ascend)
- `cuda`: Use CUDA GPU acceleration
- `ascend`: Use Huawei Ascend NPU
