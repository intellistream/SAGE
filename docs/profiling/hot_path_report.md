# SAGE Hot-Path Profiling Report

> Status: historical report content reset during main-repo consolidation.

This file is intentionally kept as a lightweight placeholder for regenerated profiling output.

Current profiling surfaces should be reported against the consolidated in-tree modules:

- `sage.runtime.scheduler`
- `sage.stream._runtime_kernel_types`
- `sage.foundation` / stream I/O helpers
- optional external capability adapters when explicitly benchmarked

To regenerate a fresh report:

```bash
python tools/profiling/cprofile_runner.py
python tools/profiling/cprofile_runner.py --heavy
```

Generated artifacts should describe the current consolidated `isage` package rather than the retired
split-package layout.
