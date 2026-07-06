# Runtime Provenance

- Ascend/NPU runtime, dev-hub, Docker/container, device-mount, CANN, and
  torch_npu environment-management changes for this repository must be made in
  `third_party/ascend-runtime-manager`.
- That directory is a real Git submodule on the repository-specific branch
  `feature/semantic-mapreduce-runtime-integration`; do not replace it with a
  symlink to `/home/<user>/ascend-runtime-manager` or any shared checkout.
- If another checkout contains a useful runtime fix, port the patch into
  `third_party/ascend-runtime-manager` and commit it on the submodule feature
  branch. Do not depend on external filesystem state for experiments.
