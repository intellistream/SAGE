# Compiled workflow plans

`sage.runtime.CompiledPlanCache` separates immutable workflow construction from
per-request binding. Use it for interactive workloads that repeatedly execute
the same operator DAG under different inputs, identities, deadlines, evidence,
or cancellation tokens.

```python
from sage.runtime import CompiledPlanCache, PlanFingerprint, bind_compiled_plan

cache = CompiledPlanCache(max_entries=128, ttl_seconds=900)
fingerprint = PlanFingerprint.build(
    operator_dag=[{"id": "load"}, {"id": "transform", "after": ["load"]}],
    schema={"input": "Record", "output": "Result"},
    policy_version="2026-08",
    capabilities={"transform": "v2"},
    retrieval_contract={"kind": "none"},
    resource_class="interactive",
)
plan = cache.get_or_compile(fingerprint, compile_static_dag)
run = bind_compiled_plan(plan, request_context, bind_request)
result = run.execute()
```

Only structural data belongs in `PlanFingerprint`. Request input, user identity,
trace ID, deadline, retrieved evidence, and cancellation tokens must be passed
to `bind_compiled_plan` and must not be captured by `compile_static_dag`.

The cache provides bounded LRU capacity, positive and negative TTLs,
single-flight compilation, and a `stats()` snapshot. A policy, schema,
capability, retrieval-contract, resource-class, or compiler-version change
produces a different digest and therefore invalidates the old plan naturally.

This API is the cache foundation. Runtime-specific compiler integration should
wrap an immutable compiled artifact and keep execution handles or request state
outside the cached object.

Flow declarations provide that integration directly:

```python
bound = declared_flow.bind_reusable(
    "structural-stage-variant",
    in_=request_input_topic,
    out=request_output_topic,
    schema={"input": "Record", "output": "Result"},
    policy_version="2026-08",
    capabilities={"transform": "v2"},
    retrieval_contract={"kind": "none"},
    resource_class="interactive",
)
```

The structural arguments participate in the fingerprint. The IO bindings do
not: each returned `BoundFlowDeclaration` points to the same immutable
`FlowProgram` while retaining its own request topics. Use
`compiled_plan_cache_stats()` for hit/miss/compile telemetry and
`clear_compiled_plan_cache()` for explicit operational invalidation.
