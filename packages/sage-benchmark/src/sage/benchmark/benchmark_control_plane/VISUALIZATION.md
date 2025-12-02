# Visualization Guide

This document describes the chart types, report formats, and visualization options available in the
Control Plane Benchmark module.

## Overview

The visualization module provides:
- **Charts**: Matplotlib-based charts for metrics visualization
- **Reports**: HTML and Markdown reports with embedded charts
- **Templates**: Customizable Jinja2 templates for reports

## Chart Types

### 1. Throughput Charts

#### Throughput Comparison (`plot_throughput_comparison`)

Bar chart comparing throughput across different scheduling policies.

```python
from sage.benchmark.benchmark_control_plane.visualization import BenchmarkCharts

charts = BenchmarkCharts(output_dir="./charts")
charts.plot_throughput_comparison(
    policy_metrics={
        "fifo": {"throughput": {"requests_per_second": 95.2}},
        "priority": {"throughput": {"requests_per_second": 94.1}},
        "slo_aware": {"throughput": {"requests_per_second": 91.3}},
    },
    title="Throughput Comparison by Policy"
)
```

**Output**: `throughput_comparison.png`

![Throughput Comparison](./visualization/templates/images/throughput_comparison_example.png)

#### Throughput vs Request Rate (`plot_throughput_vs_rate`)

Line chart showing throughput at different request rates.

```python
charts.plot_throughput_vs_rate(
    rate_results=[
        (10.0, 9.8),
        (50.0, 48.5),
        (100.0, 95.2),
        (200.0, 178.3),
    ],
    title="Throughput vs Request Rate"
)
```

**Output**: `throughput_vs_rate.png`

### 2. Latency Charts

#### Latency Distribution (`plot_latency_distribution`)

Histogram showing the distribution of end-to-end latencies.

```python
charts.plot_latency_distribution(
    latencies=[120, 135, 142, 156, 189, 210, ...],  # ms
    title="Latency Distribution - FIFO Policy"
)
```

**Output**: `latency_distribution.png`

#### Latency Percentiles (`plot_latency_percentiles`)

Bar chart comparing latency percentiles (p50, p90, p95, p99) across policies.

```python
charts.plot_latency_percentiles(
    policy_percentiles={
        "fifo": {"p50": 142, "p90": 289, "p95": 356, "p99": 423},
        "priority": {"p50": 148, "p90": 301, "p95": 378, "p99": 445},
        "slo_aware": {"p50": 135, "p90": 267, "p95": 312, "p99": 389},
    },
    title="Latency Percentiles by Policy"
)
```

**Output**: `latency_percentiles.png`

#### Latency CDF (`plot_latency_cdf`)

Cumulative Distribution Function (CDF) of latencies.

```python
charts.plot_latency_cdf(
    policy_latencies={
        "fifo": [120, 135, 142, ...],
        "priority": [125, 138, 148, ...],
        "slo_aware": [115, 128, 135, ...],
    },
    title="Latency CDF Comparison"
)
```

**Output**: `latency_cdf.png`

### 3. SLO Charts

#### SLO Compliance (`plot_slo_compliance`)

Bar chart showing SLO compliance rates across policies.

```python
charts.plot_slo_compliance(
    policy_slo_rates={
        "fifo": 0.712,
        "priority": 0.768,
        "slo_aware": 0.885,
    },
    title="SLO Compliance by Policy"
)
```

**Output**: `slo_compliance.png`

#### SLO by Priority (`plot_slo_by_priority`)

Grouped bar chart showing SLO compliance by request priority.

```python
charts.plot_slo_by_priority(
    policy_priority_slo={
        "fifo": {"HIGH": 0.65, "NORMAL": 0.72, "LOW": 0.78},
        "priority": {"HIGH": 0.89, "NORMAL": 0.75, "LOW": 0.62},
        "slo_aware": {"HIGH": 0.95, "NORMAL": 0.88, "LOW": 0.82},
    },
    title="SLO Compliance by Priority Level"
)
```

**Output**: `slo_by_priority.png`

### 4. Resource Charts

#### GPU Utilization (`plot_gpu_utilization`)

Time series plot of GPU utilization during benchmark.

```python
charts.plot_gpu_utilization(
    timestamps=[0, 1, 2, 3, 4, ...],  # seconds
    utilization=[45, 67, 82, 91, 88, ...],  # percent
    title="GPU Utilization Over Time"
)
```

**Output**: `gpu_utilization.png`

#### GPU Memory (`plot_gpu_memory`)

Time series plot of GPU memory usage.

```python
charts.plot_gpu_memory(
    timestamps=[0, 1, 2, 3, 4, ...],
    memory_used=[4.2, 5.8, 7.1, 8.3, 8.5, ...],  # GB
    memory_total=24.0,  # GB
    title="GPU Memory Usage"
)
```

**Output**: `gpu_memory.png`

### 5. Hybrid-Specific Charts

#### Mixed Ratio Impact (`plot_mixed_ratio_impact`)

Line chart showing performance impact of different LLM/Embedding ratios.

```python
charts.plot_mixed_ratio_impact(
    ratio_results={
        "throughput": [(0.0, 120), (0.25, 115), (0.5, 105), (0.75, 98), (1.0, 92)],
        "llm_slo": [(0.0, 0.0), (0.25, 0.92), (0.5, 0.88), (0.75, 0.82), (1.0, 0.78)],
        "emb_slo": [(0.0, 0.98), (0.25, 0.96), (0.5, 0.94), (0.75, 0.0), (1.0, 0.0)],
    },
    title="Performance vs LLM/Embedding Ratio"
)
```

**Output**: `mixed_ratio_impact.png`

#### Embedding Batch Efficiency (`plot_embedding_batch_efficiency`)

Bar chart showing embedding batch efficiency metrics.

```python
charts.plot_embedding_batch_efficiency(
    batch_metrics={
        "fifo": {"avg_batch_size": 18.5, "batch_utilization": 0.58},
        "hybrid_slo": {"avg_batch_size": 28.3, "batch_utilization": 0.88},
    },
    title="Embedding Batch Efficiency"
)
```

**Output**: `embedding_batch_efficiency.png`

#### Request Type Breakdown (`plot_type_breakdown`)

Pie chart showing the breakdown of request types.

```python
charts.plot_type_breakdown(
    type_counts={
        "llm_chat": 450,
        "llm_generate": 250,
        "embedding": 300,
    },
    title="Request Type Distribution"
)
```

**Output**: `type_breakdown.png`

## Report Formats

### HTML Report

Interactive HTML report with:
- Configuration summary
- Metrics tables
- Embedded chart images
- Policy comparison
- Conclusions

```python
from sage.benchmark.benchmark_control_plane.visualization import ReportGenerator

report_gen = ReportGenerator(
    result=benchmark_result,
    charts_dir=Path("./charts")
)
report_gen.generate_html_report(Path("./report.html"))
```

**Template**: `visualization/templates/benchmark_report.html`

#### HTML Report Structure

```html
<!DOCTYPE html>
<html>
<head>
    <title>Benchmark Report</title>
    <style>/* Embedded CSS */</style>
</head>
<body>
    <header>
        <h1>sageLLM Control Plane Benchmark Report</h1>
        <p>Generated: {{ timestamp }}</p>
    </header>

    <section id="config">
        <h2>Configuration</h2>
        <table><!-- Config details --></table>
    </section>

    <section id="summary">
        <h2>Summary</h2>
        <table><!-- Summary metrics --></table>
    </section>

    <section id="charts">
        <h2>Charts</h2>
        <img src="charts/throughput_comparison.png" />
        <img src="charts/latency_distribution.png" />
        <!-- More charts -->
    </section>

    <section id="detailed">
        <h2>Detailed Results</h2>
        <!-- Per-policy results -->
    </section>

    <section id="conclusions">
        <h2>Conclusions</h2>
        <ul>
            <li>Best throughput: {{ best_throughput.policy }}</li>
            <li>Best SLO compliance: {{ best_slo.policy }}</li>
        </ul>
    </section>
</body>
</html>
```

### Markdown Report

Markdown format suitable for documentation and GitHub:

```python
report_gen.generate_markdown_report(Path("./report.md"))
```

**Output Format**:

```markdown
# sageLLM Control Plane Benchmark Report

**Generated**: 2025-11-28 15:30:45

## Configuration

| Parameter | Value |
|-----------|-------|
| Control Plane URL | http://localhost:8080 |
| Requests | 1000 |
| Request Rate | 100 req/s |
| LLM Ratio | 70% |

## Summary

| Policy | Throughput | Avg Latency | P99 Latency | SLO Rate | Errors |
|--------|------------|-------------|-------------|----------|--------|
| fifo | 95.2 req/s | 156 ms | 423 ms | 71.2% | 0.3% |
| hybrid_slo | 98.5 req/s | 132 ms | 312 ms | 93.7% | 0.1% |

## Charts

### Throughput Comparison
![Throughput](charts/throughput_comparison.png)

### Latency Distribution
![Latency](charts/latency_distribution.png)

## Conclusions

- **Best Throughput**: hybrid_slo (98.5 req/s)
- **Best SLO Compliance**: hybrid_slo (93.7%)
- **Best P99 Latency**: hybrid_slo (312 ms)
```

## Generating All Charts

Use `generate_all_charts()` to create all relevant charts at once:

```python
from sage.benchmark.benchmark_control_plane.visualization import BenchmarkCharts

charts = BenchmarkCharts(output_dir="./charts")
chart_paths = charts.generate_all_charts(
    policy_metrics={
        "fifo": {...},
        "hybrid_slo": {...},
    },
    latency_data={...},
    slo_data={...},
    gpu_data={...},  # Optional
)

print(f"Generated {len(chart_paths)} charts")
for path in chart_paths:
    print(f"  - {path}")
```

## Customization

### Chart Style

Customize chart appearance:

```python
charts = BenchmarkCharts(
    output_dir="./charts",
    style="seaborn",  # matplotlib style
    figsize=(12, 8),  # default figure size
    dpi=150,          # resolution
)
```

### Template Customization

Create custom templates in `visualization/templates/`:

1. Copy existing template
2. Modify HTML/CSS
3. Use in ReportGenerator:

```python
report_gen = ReportGenerator(
    result=result,
    charts_dir=charts_dir,
    template_name="my_custom_template.html"  # Custom template
)
```

### Available Template Variables

| Variable | Type | Description |
|----------|------|-------------|
| `timestamp` | string | Report generation time |
| `config` | dict | Benchmark configuration |
| `policy_results` | dict | Per-policy results |
| `summary` | dict | Summary statistics |
| `charts` | list | List of chart filenames |
| `best_throughput` | dict | Best throughput policy/value |
| `best_slo` | dict | Best SLO policy/value |
| `best_latency` | dict | Best latency policy/value |

## CLI Integration

Generate visualizations from CLI:

```bash
# Generate all formats
sage-cp-bench visualize --input results.json --output ./viz --format all

# Generate only charts
sage-cp-bench visualize --input results.json --format charts

# Generate only HTML report
sage-cp-bench visualize --input results.json --format html

# Generate only Markdown report
sage-cp-bench visualize --input results.json --format markdown
```

## Dependencies

Required packages:
- `matplotlib>=3.5.0` - Chart generation
- `jinja2>=3.0.0` - HTML template rendering

Optional packages:
- `plotly>=5.0.0` - Interactive charts (future)
- `seaborn>=0.12.0` - Enhanced chart styles

Install with:
```bash
pip install matplotlib jinja2
# Or
pip install isage-benchmark[visualization]
```

## Troubleshooting

### Charts Not Generating

1. Check matplotlib is installed: `pip install matplotlib`
2. For headless servers, set backend:
   ```python
   import matplotlib
   matplotlib.use('Agg')
   ```

### Template Not Found

1. Ensure templates directory exists
2. Check template path in ReportGenerator
3. Use absolute path if needed

### Low Resolution Images

Increase DPI when creating charts:
```python
charts = BenchmarkCharts(output_dir="./charts", dpi=300)
```

---

*Updated: 2025-11-28*
