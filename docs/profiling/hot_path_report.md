# SAGE Hot-Path Profiling Report

> Generated: 2026-02-27 23:36\
> Issue: [#1467](https://github.com/intellistream/SAGE/issues/1467)\
> Feeds into: [#1468](https://github.com/intellistream/SAGE/issues/1468) (isage-kernel C++) ·
> [#1469](https://github.com/intellistream/SAGE/issues/1469) (isage-libs C++)

______________________________________________________________________

## Executive Summary

| Hot Path                        | Package                      | Measured | Threshold | Verdict                            |
| ------------------------------- | ---------------------------- | -------- | --------- | ---------------------------------- |
| Scheduler — RoundRobin decision | `isage-kernel/scheduler`     | 1.88µs   | 0.50µs    | 🔴 **HIGH** — C++ port recommended |
| Scheduler — Priority decision   | `isage-kernel/scheduler`     | 6.25µs   | 1.00µs    | 🔴 **HIGH** — C++ port recommended |
| Comm — Packet construction      | `isage-kernel/communication` | 0.99µs   | 0.20µs    | 🔴 **HIGH** — C++ port recommended |
| Comm — msgpack serialize        | `isage-kernel/communication` | 0.32µs   | 1.00µs    | 🟢 LOW — skip for now              |
| Comm — msgpack deserialize      | `isage-kernel/communication` | 0.59µs   | 1.00µs    | 🟢 LOW — skip for now              |
| Comm — Key routing              | `isage-kernel/communication` | 0.87µs   | 0.10µs    | 🔴 **HIGH** — C++ port recommended |
| DP — Vector perturbation        | `isage-libs/privacy`         | 29.45ms  | 5.00ms    | 🔴 **HIGH** — C++ port recommended |
| DP — Neighbor compensation      | `isage-libs/privacy`         | 16.50µs  | 50.00ms   | 🟢 LOW — skip for now              |
| DP — Full engine call           | `isage-libs/privacy`         | 91.52µs  | 100.00ms  | 🟢 LOW — skip for now              |
| IO — Batch assembly             | `isage-libs/foundation/io`   | 1.45µs   | 2.00µs    | 🟢 LOW — skip for now              |
| IO — JSON roundtrip             | `isage-libs/foundation/io`   | 25.96µs  | 10.00µs   | 🔴 **HIGH** — C++ port recommended |
| IO — Queue enqueue              | `isage-libs/foundation/io`   | 6.24µs   | 0.50µs    | 🔴 **HIGH** — C++ port recommended |

______________________________________________________________________

## Recommendations

### 🔴 Worth C++-porting (HIGH priority)

- **Scheduler — RoundRobin decision** (isage-kernel/scheduler) — 1.88µs
- **Scheduler — Priority decision** (isage-kernel/scheduler) — 6.25µs
- **Comm — Packet construction** (isage-kernel/communication) — 0.99µs
- **Comm — Key routing** (isage-kernel/communication) — 0.87µs
- **DP — Vector perturbation** (isage-libs/privacy) — 29.45ms
- **IO — JSON roundtrip** (isage-libs/foundation/io) — 25.96µs
- **IO — Queue enqueue** (isage-libs/foundation/io) — 6.24µs

### 🟡 Profile deeper before deciding (MED priority)

- *(none in medium range)*

### 🟢 Not worth porting yet (LOW / skip)

- Comm — msgpack serialize (isage-kernel/communication) — 0.32µs
- Comm — msgpack deserialize (isage-kernel/communication) — 0.59µs
- DP — Neighbor compensation (isage-libs/privacy) — 16.50µs
- DP — Full engine call (isage-libs/privacy) — 91.52µs
- IO — Batch assembly (isage-libs/foundation/io) — 1.45µs

______________________________________________________________________

## Per-Path Detail

### Scheduler / Task Dispatch (`isage-kernel`)

| Metric                | Value  |
| --------------------- | ------ |
| `rr_total_s`          | 0.0939 |
| `rr_per_decision_us`  | 1.8773 |
| `pri_total_s`         | 0.3123 |
| `pri_per_decision_us` | 6.2461 |
| `wall_time_s`         | 0.4136 |

### Communication / Packet Serialization (`isage-kernel`)

| Metric                  | Value  |
| ----------------------- | ------ |
| `payload_size_bytes`    | 1024   |
| `pkt_construct_total_s` | 0.0991 |
| `pkt_construct_us`      | 0.9912 |
| `msgpack_ser_total_s`   | 0.0325 |
| `msgpack_ser_us`        | 0.3247 |
| `msgpack_deser_total_s` | 0.0586 |
| `msgpack_deser_us`      | 0.5860 |
| `route_total_s`         | 0.0871 |
| `route_us`              | 0.8715 |
| `wall_time_s`           | 0.2812 |

### DP Unlearning (`isage-libs/privacy`)

| Metric                   | Value         |
| ------------------------ | ------------- |
| `num_vectors`            | 5000          |
| `dim`                    | 128           |
| `perturb_total_s`        | 0.2945        |
| `perturb_ms_per_call`    | 29.4544       |
| `acct_total_s`           | 0.0062        |
| `acct_us_per_call`       | 6.1573        |
| `comp_total_s`           | 0.0002        |
| `comp_ms_per_call`       | 0.0165        |
| `engine_total_s`         | 0.0009        |
| `engine_ms_per_call`     | 0.0915        |
| `engine_vectors_per_sec` | 54630121.4785 |
| `wall_time_s`            | 0.3435        |

### Foundation I/O (`isage-libs/foundation/io`)

| Metric                   | Value   |
| ------------------------ | ------- |
| `batch_size`             | 256     |
| `batch_assembly_total_s` | 0.0145  |
| `batch_assembly_us`      | 1.4531  |
| `batches_flushed`        | 39      |
| `queue_enq_total_s`      | 0.0624  |
| `queue_enq_us`           | 6.2432  |
| `queue_deq_total_s`      | 0.0702  |
| `queue_deq_us`           | 7.0245  |
| `json_roundtrip_total_s` | 0.2596  |
| `json_roundtrip_us`      | 25.9592 |
| `file_write_total_s`     | 0.0090  |
| `file_write_us`          | 0.8998  |
| `file_read_total_s`      | 0.0045  |
| `file_read_us`           | 0.4457  |
| `wall_time_s`            | 0.4235  |

______________________________________________________________________

## How to Re-run

```bash
# From SAGE repo root
python tools/profiling/cprofile_runner.py

# Heavy mode (larger workloads)
python tools/profiling/cprofile_runner.py --heavy

# Single path
python tools/profiling/cprofile_runner.py --path dp_unlearning

# Flame graph via py-spy (requires: pip install py-spy)
bash tools/profiling/flame_graph.sh dp_unlearning
```

## Notes

- Measurements are wall-clock (perf_counter), not CPU-only.
- DP Unlearning benchmarks include NumPy allocation; C++ target should reuse pre-allocated buffers.
- Communication benchmarks include stub Packet (no real network); validate with actual Flownet traffic.
- See `.prof` files in `tools/profiling/reports/` for deep dives with `snakeviz` or `gprof2dot`.
