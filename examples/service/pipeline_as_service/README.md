# Pipeline-as-Service Demo

These examples show how to register an entire SAGE pipeline as a service while
still leveraging the same service invocation helpers for its internal stages.
Each scenario adds a different client pattern so you can see how pipelines and
services compose in more realistic setups.

## What it demonstrates

- **Pipeline as a service** – The decision pipeline is registered as the
  `order_pipeline` service and can be invoked via `call_service`.
- **Asynchronous invocation** – Operators can use
  `self.call_service_async(...)` to overlap work and wait on a `Future`.
- **Service-to-service orchestration** – The pipeline calls supporting services
  (feature store, risk scoring) using the same helpers.
- **Cooperative shutdown** – Sending a `{"command": "shutdown"}` message tells
  the pipeline to stop after finishing in-flight work.

## Files

- `hello_pipeline_as_service.py` – Creates the service-backed decision pipeline
  plus a driver pipeline that submits orders and prints the returned decisions.
- `async_client_pipeline_as_service.py` – Uses `call_service_async` to submit a
  burst of requests concurrently and wait for futures to resolve.
- `multi_client_pipeline_as_service.py` – Spawns two driver pipelines (new vs
  returning users) that share the same pipeline service endpoint.
- `pipeline_bridge.py` – Shared queue bridge used to pass requests between the
  driver pipelines and the service-backed pipeline.

## How to run

From the repository root you can run any scenario. For example:

```bash
python examples/service/pipeline_as_service/hello_pipeline_as_service.py
python examples/service/pipeline_as_service/async_client_pipeline_as_service.py
python examples/service/pipeline_as_service/multi_client_pipeline_as_service.py
```

You should see log output from both the service-backed pipeline and the client
pipelines, including enrichment, scoring, service replies, and a shutdown
acknowledgement once all work completes.
