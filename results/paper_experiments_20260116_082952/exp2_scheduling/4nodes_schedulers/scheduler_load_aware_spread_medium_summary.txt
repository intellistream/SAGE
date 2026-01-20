======================================================================
Benchmark Results: scheduler_load_aware_spread_medium
======================================================================
Timestamp: 2026-01-16T09:33:09.696179

Configuration:
  experiment_name: scheduler_load_aware_spread_medium
  num_tasks: 200
  task_complexity: medium
  parallelism: 16
  num_nodes: 4
  scheduler_type: load_aware
  scheduler_strategy: spread
  use_remote: True
  pipeline_stages: 3
  enable_rag: True
  enable_llm: True

Results:
  Total Tasks:       200
  Successful:        200
  Failed:            0
  Duration:          12.13s

  Throughput:        16.49 tasks/sec
  Avg Latency:       645.77 ms
  P50 Latency:       646.68 ms
  P95 Latency:       1070.86 ms
  P99 Latency:       1138.14 ms

  Scheduling Latency: 0.00 ms
  Queue Latency:      0.00 ms
  Execution Latency:  0.00 ms

  Node Balance:      96.00%

  Node Distribution:
    sage-node-1: 12 (6.0%)
    sage-node-10: 13 (6.5%)
    sage-node-11: 13 (6.5%)
    sage-node-12: 13 (6.5%)
    sage-node-13: 13 (6.5%)
    sage-node-14: 12 (6.0%)
    sage-node-15: 13 (6.5%)
    sage-node-16: 12 (6.0%)
    sage-node-2: 12 (6.0%)
    sage-node-3: 12 (6.0%)
    sage-node-4: 12 (6.0%)
    sage-node-5: 12 (6.0%)
    sage-node-6: 12 (6.0%)
    sage-node-7: 13 (6.5%)
    sage-node-8: 13 (6.5%)
    sage-node-9: 13 (6.5%)

======================================================================
