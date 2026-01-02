# Pending Actions (Stage 2 & Stage 3)

## Stage 2 – Quality Improvements (Remaining)

- Hardware capability checks (beyond FP8):
  - Validate embedding/LLM engine startup against GPU/CPU capability (compute capability, memory),
    surface clear errors.
  - Add preflight warnings for unsupported hardware paths (e.g., missing CUDA for INT8/FP16 accel,
    insufficient VRAM for configured model sizes).
- Exception message unification:
  - Standardize error shape/fields across service entrypoints (gateway/engine), KV runtime, and
    accelerator modules; ensure actionable context (component, input params, remediation hints).
- MFU verification:
  - Current formula updated (seq_len-aware); add coverage across more model sizes/seq_len to prevent
    regressions.

## Stage 3 – Engineering Improvements (Remaining)

- Thread safety and concurrency:
  - Add locks/atomicity where shared state is mutated (KV pool/tiered storage, control-plane
    registries, engine lifecycle management).
  - Introduce concurrent access tests (multi-thread/process) for KV cache and cross-request reuse.
- Test coverage expansion:
  - Failure-path tests (allocation failures, migration errors, hardware-mismatch scenarios).
  - Hardware-specific tests (mocked capabilities for sparsity/quantization/engine startup).
- Time API unification:
  - Centralize timestamp API to avoid mixed `time.time()` usage; ensure monotonic clocks for
    latency/metrics.

## Notes

- FP8 hardware gating is implemented; extend similar checks to other accelerators.
- Hot/cold classifier now decay-aware; consider exposing thresholds via config and adding perf
  benchmarks.
