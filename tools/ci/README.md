# Run CI Locally

This folder contains a lightweight script to reproduce the key steps of our GitHub CI on your machine.

## Quick start

- Unified entrypoint (recommended):

```bash
tools/ci/ci.sh run
```

- Default run (mirrors CI steps with sensible defaults):

```bash
bash tools/ci/run_local_ci.sh
```

- Disable heavy parts:

```bash
BUILD_CPP_DEPS=0 RUN_EXAMPLES=0 RUN_PYPI_VALIDATE=0 bash tools/ci/run_local_ci.sh
```

### Tunables (environment variables)

- `PYTHON_BIN`: Python executable (default: `python3`)
- `BUILD_CPP_DEPS`: Install build-essential/cmake/pkg-config if needed (default: `1`)
- `RUN_EXAMPLES`: Run examples test suite (default: `1`)
- `RUN_CODE_QUALITY`: Run black/isort/flake8 if available (default: `1`)
- `RUN_IMPORT_TESTS`: Run import + CLI checks (default: `1`)
- `RUN_PYPI_VALIDATE`: Run `sage dev pypi validate` (heavy/long) (default: `0`)

Notes:
- The script calls `./quickstart.sh --dev --pip --yes` like CI. Have network access available.
- On non-Debian systems, system deps installation is skipped automatically (no `apt-get`).
- For examples, we set `SAGE_EXAMPLES_MODE=test` to minimize external requirements while still exercising the important paths.

## Alternative: run the actual GitHub workflow with `act`

If you prefer to execute the real GitHub Actions workflow locally, you can use [`act`](https://github.com/nektos/act).

1. Install act (see their README)
2. From the repo root, run:

```bash
act -j test
```

Tips:
- For secrets (HF_TOKEN, etc.), create a `.secrets` file or pass with `--secret` flags.
- You may need a Docker image with Python 3.11 and build tools. For example:

```bash
act -j test -P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-latest
```

The provided `run_local_ci.sh` is faster to iterate with day-to-day; `act` is useful when you want to replicate the full workflow logic in containers. You can also use the unified entry:

```bash
tools/ci/ci.sh act -j test
```

If in doubt, start with the unified entrypoint:

```bash
tools/ci/ci.sh help
```
