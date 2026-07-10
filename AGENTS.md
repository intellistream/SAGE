# Runtime Provenance

- Use the project-specific conda environment for Semantic MapReduce / SAGE
  experiments. The expected environment name is `esage-vllm-hust-dev`; it may
  be cloned from `vllm-hust-dev`, but do not install SAGE overlays, editable
  packages, patches, or experiment-only dependencies directly into the shared
  `vllm-hust-dev` environment.
- Vendored runtime submodule changes must be made on project-specific
  `feature/<project-or-optimization-name>-<purpose>` branches. Do not create
  `codex/...` branches inside submodules.
- Ascend/NPU runtime, dev-hub, Docker/container, device-mount, CANN, and
  torch_npu environment-management changes for this repository must be made in
  `third_party/ascend-runtime-manager`.
- That directory is a real Git submodule on the repository-specific branch
  `feature/semantic-mapreduce-runtime-integration`; do not replace it with a
  symlink to `/home/<user>/ascend-runtime-manager` or any shared checkout.
- If another checkout contains a useful runtime fix, port the patch into
  `third_party/ascend-runtime-manager` and commit it on the submodule feature
  branch. Do not depend on external filesystem state for experiments.
- Shared reusable serving workloads may be consumed from the real Git submodule
  `third_party/llm-serving-workloads`. SAGE-specific Semantic MapReduce
  workloads may remain repo-local when they exercise semantic-reduction
  mechanisms, stress cases, negative cases, or ablations that are unique to
  this project.
- Experiment manifests must record the workload source: either the
  `third_party/llm-serving-workloads` commit/path for shared workloads, or the
  repo-local workload path for SAGE-specific workloads. Real-online results
  must also label the evidence type (`real-online`, `existing-server-probe`,
  `replay`, `simulation/model`, `projected-profile`, or `derived-artifact`).
