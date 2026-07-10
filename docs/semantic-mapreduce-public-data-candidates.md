# Public Data Candidates for Semantic MapReduce

This note records public datasets and benchmark substrates that can replace or
complement the current controlled telemetry generator. The current repository
includes a source-level probe for these candidates, but none of them has been
used in the paper's reported reducer-quality numbers yet.

## Selection Criteria

- Contains operational signals relevant to incident analysis: metrics, logs,
  traces, service graphs, fault labels, or anomaly injection metadata.
- Can be mapped into the existing Semantic MapReduce contract:
  `Shard`, `MapEvidence`, `Normalize`, `GroupEvidence`, `SemanticReduce`, and
  `ReportTrace`.
- Provides enough provenance to score at least one of: root service, time
  overlap, affected service set, evidence links, or fault type.

## Candidate Sources

| Source | Signal Types | Why It Helps | Integration Status |
| --- | --- | --- | --- |
| AIOps Challenge 2020 Data | Business metrics, infrastructure metrics, traces, fault table | Includes fault rows with time, type, and localization plus multi-source metrics/traces. Useful for replaying labeled incident hypotheses. | Probed. GitHub README is accessible, but data archives are hosted through external cloud links, so the fault CSV/zips are not auto-downloaded by the default script. |
| LO2 microservice anomaly dataset | Logs, metrics, anomaly labels; traces discussed as part of the collection context | Large labeled microservice anomaly corpus with logs and metrics. Useful for testing multimodal `MapEvidence` and evidence compression. | Probed. Zenodo metadata, README, scripts, and appendix are accessible. `lo2-sample.zip` is about 1.07 GB and `lo2-data.zip` is about 46.5 GB, so they are skipped by the default 64 MB limit. |
| OpenTelemetry Demo | Service graph, synthetic traffic, metrics/logs/traces via OpenTelemetry stack | Good open benchmark substrate for generating repeatable service-level telemetry and validating adapters against standard observability formats. | Probed. Repository metadata and README are accessible; full evaluation requires deploying the demo and collecting telemetry. |
| Illinois/FIRM trace dataset | Preprocessed microservice traces from DeathStarBench and Train-Ticket with anomaly locations | Provides real trace-derived CSVs from Kubernetes deployments and known anomaly injection source. Useful for trace-only reducer ablations. | Probed. The current Data Bank URL returned HTTP 403 in the automated probe, so manual access or an alternate DOI/download route is needed. |
| DeathStarBench | Microservice benchmark applications | Useful for generating new traces with controllable workload, topology, and fault injection. | Probed. Repository metadata and benchmark service directories are accessible; full evaluation requires deployment and fault/trace collection. |

## Current Source-Probe Artifact

Run:

```bash
conda run -n esage-vllm-hust-dev \
  env PYTHONPATH=src \
  python tools/benchmark_carrier/probe_public_semantic_mapreduce_sources.py \
    --run-id 20260708T-public-source-probe \
    --max-download-mb 64
```

Artifact:

```text
.sage/benchmarks/public_semantic_mapreduce_sources/20260708T-public-source-probe/
```

Summary:

| Source | Accessible | Probe Result |
| --- | ---: | --- |
| `aiops-challenge-2020` | yes | README accessible; data requires external archive download. |
| `lo2` | yes | Zenodo metadata and small files downloaded; large sample/data zips skipped by size limit. |
| `opentelemetry-demo` | yes | Repository and topology hints accessible; requires deployment for telemetry. |
| `deathstarbench` | yes | Repository and service directories accessible; requires deployment for telemetry. |
| `illinois-firm-traces` | no | Automated URL probe returned HTTP 403. |

The artifact records `manifest.json`, `summary.csv`, `source_probe.json`, and
small metadata files such as READMEs and LO2 scripts/appendix. The manifest
also records the pinned `third_party/llm-serving-workloads` commit when the
submodule is present, even though this probe itself uses public source metadata
rather than a shared workload trace.

## How To Use In The Paper

Use these sources cautiously:

- It is safe to say that public replay candidates exist.
- It is safe to say that a source-level probe has verified availability or
  access blockers for each candidate.
- It is safe to cite accessible sources as external data sources that can
  replace the synthetic generator under the same evidence/reducer contract.
- Do not claim that current reported Semantic MapReduce numbers are measured on
  these datasets until loaders, manifests, and scorer mappings are committed.

## Minimal Loader Plan

1. Add a `PublicReplayRecord` schema with timestamp, service, region or node,
   metric/log/trace fields, and source URI.
2. Add one loader at a time. LO2 is easiest to probe programmatically through
   Zenodo, while AIOps Challenge 2020 is attractive because it describes fault
   rows but needs external archive download first.
3. Emit the same `EvidenceObject` fields used by the synthetic workload.
4. Preserve the original row/file/span identifiers in `source_event_refs`.
5. Reuse the existing reducer matrix and add a `dataset` field to each
   manifest.
