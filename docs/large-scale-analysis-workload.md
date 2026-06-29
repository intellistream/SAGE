# SAGE Large-Scale Analysis Workload

This workload evaluates whether SAGE can act as the orchestration layer for
large-scale data analysis with LLM-style semantic reduction.

It is not a Spark/Hadoop replacement benchmark. The goal is to measure the
AI workflow layer: partitioning, local evidence extraction, global incident
fusion, and explanation generation.

## Scenario

A production LLM serving platform emits high-volume telemetry from NPU-backed
services:

- `prefill`
- `decode`
- `kv-cache`
- `scheduler`
- `router`
- `embedding`

Each event contains service, tenant, region, latency, error flag, NPU
utilization, and queue depth. The generator injects hidden incidents such as:

- latency spikes
- NPU saturation
- queue backlog

The workload asks the system to recover these incidents from the event stream.

## Pipeline

1. **Generate data**: synthesize an event stream and ground-truth incidents.
2. **Map**: split events into shards and compute local anomaly candidates per
   service, region, and time window.
3. **Reduce**: merge candidates across shards and cluster adjacent windows into
   incident-level hypotheses.
4. **Explain**: produce a concise natural-language summary for each incident.
5. **Score**: compare detected incidents against injected ground truth.

This mirrors a MapReduce-like SAGE workload: the expensive data scan is
partitionable, while the semantic reduce step fuses evidence into structured
insights.

## Metrics

- `precision`: fraction of reported incidents that match injected incidents.
- `recall`: fraction of injected incidents recovered.
- `f1`: harmonic mean of precision and recall.
- `evidence_coverage`: average evidence events per detected incident.
- `map_duration_ms`, `reduce_duration_ms`, `total_duration_ms`.
- `throughput_events_per_s`.

## Run

```bash
PYTHONPATH=src python tools/benchmark_carrier/run_large_scale_analysis_workload.py \
  --events 50000 \
  --shards 16 \
  --seed 7 \
  --top-k 12
```

For a larger smoke run:

```bash
PYTHONPATH=src python tools/benchmark_carrier/run_large_scale_analysis_workload.py \
  --events 100000 \
  --shards 32 \
  --seed 7 \
  --top-k 16
```

## Baseline Result

On 2026-06-29, the deterministic baseline produced:

| events | shards | precision | recall | f1 | throughput events/s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 50,000 | 16 | 1.0000 | 1.0000 | 1.0000 | ~106k |
| 100,000 | 32 | 1.0000 | 0.7500 | 0.8571 | ~106k |

The 100k case is intentionally non-trivial: one injected incident is missed by
the current deterministic thresholds, leaving room for a true LLM/SAGE semantic
reducer to improve recall without flooding operators with false positives.

## Positioning

This workload is meant to show that SAGE can sit above data systems as an
AI-native orchestration layer:

- external systems can do scans, joins, vector retrieval, or distributed compute;
- SAGE coordinates the map/reduce-style analysis stages;
- an LLM can be inserted at the reduce/explain stage to produce structured,
  auditable conclusions.
