# Installation Validation Guide

This page describes the new `tools/install/tests/verify_installation.sh` harness and how it helps
ensure a reliable SAGE installation.

## What it does

The verification script runs a concise but broad set of checks that are safe for developer and CI
systems:

1. **Python environment** – confirms the Python interpreter and `pip` are available.
1. **Core package imports** – ensures `sage`, `sage.kernel`, `sage.libs`, and `sage.middleware` can
   all be imported.
1. **Critical dependencies** – validates `numpy`, `pandas`, `torch`, and `transformers` are
   installed.
1. **Version alignment** – checks that the core packages report identical versions.
1. **CLI presence** – confirms the `sage` and `sage-dev` CLIs are on `PATH`.
1. **Optional extras** – reports vLLM availability and GPU/CUDA detection.
1. **Configuration and sample** – verifies `.env` coverage and runs
   `examples/tutorials/hello_world.py` with a timeout.
1. **Environment health** – adds `pip check`, caches, and key environment variable inspections to
   guard against tampered environments.

Every section prints a compact summary and exits non-zero if a **critical** test fails.

## Running the script locally

```bash
bash tools/install/tests/verify_installation.sh
```

The script can be safely run after a fresh `./quickstart.sh` execution or before packaging a
release. To keep the job fast in constrained environments, it uses a 30-second timeout when running
the example and silences optional component failures.

## CI integration

`build-test.yml` now includes a dedicated step to execute the validation suite right after the
installation step:

```yaml
- name: Run installation validation suite
  run: |
    echo "🔍 Running installation verification suite..."
    bash tools/install/tests/verify_installation.sh
```

This ensures pull requests and pushes always validate both install and runtime paths before running
the heavier test suite.

## Expectations and troubleshooting

- The script writes additional diagnostics to stdout; check the GitHub Actions log under "Run
  installation validation suite" if a check fails.
- Network-dependent components (like `hello_world.py`) are wrapped in a warning-only block, so
  failures here will not fail the job but will be highlighted for manual follow-up.
- If the environmental health checks fail, ensure a clean virtual environment is used and that
  `PYTHONNOUSERSITE=1` is exported to avoid leaking user packages.

## Customization

You can tweak the script to skip long sections in edge cases:

- Export `SAGE_VALIDATION_SKIP_EXAMPLE=true` before running to skip the example run.
- Export `SAGE_VALIDATION_VERBOSE=true` to keep the raw output visible even when tests pass.
- Add extra runtime checks at the bottom (e.g., verifying `sage doctor` output) for more specific
  deployments.
