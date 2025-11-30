# Setup SAGE Action

A reusable GitHub Action for setting up the SAGE framework consistently across all workflows.

## Why This Action?

Previously, different workflows had their own SAGE installation logic, leading to:
- Inconsistent installation methods between `build-test.yml`, `paper1-experiments.yml`, etc.
- Some workflows failing while others succeed with the same code
- Duplicated installation code that's hard to maintain

This action centralizes the installation logic to ensure consistency.

## Usage

### Basic Usage

```yaml
steps:
  - uses: actions/checkout@v4
    with:
      submodules: 'recursive'

  - name: Setup SAGE
    uses: ./.github/actions/setup-sage
    with:
      install-mode: 'dev'  # or 'core', 'standard'
```

### With All Options

```yaml
steps:
  - uses: actions/checkout@v4
    with:
      submodules: 'recursive'

  - name: Setup SAGE
    uses: ./.github/actions/setup-sage
    with:
      install-mode: 'dev'
      python-version: '3.11'
      skip-system-deps: 'false'
      hf-token: ${{ secrets.HF_TOKEN }}
      create-env-file: 'true'
```

### Using Outputs

```yaml
steps:
  - name: Setup SAGE
    id: setup
    uses: ./.github/actions/setup-sage

  - name: Check Results
    run: |
      echo "SAGE Version: ${{ steps.setup.outputs.sage-version }}"
      echo "C++ Extensions: ${{ steps.setup.outputs.cpp-extensions-available }}"
```

## Inputs

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `install-mode` | Installation mode: `core`, `standard`, or `dev` | `dev` | No |
| `python-version` | Python version (GitHub-hosted runners only) | `3.11` | No |
| `skip-system-deps` | Skip system dependency installation | `false` | No |
| `hf-token` | HuggingFace token for model downloads | `''` | No |
| `create-env-file` | Create .env file with provided settings | `false` | No |
| `env-file-content` | Custom .env content (base64 encoded) | `''` | No |

## Outputs

| Output | Description |
|--------|-------------|
| `sage-version` | Installed SAGE version |
| `cpp-extensions-available` | Whether C++ extensions are available (`true`/`false`) |

## What This Action Does

1. **Setup Python** (GitHub-hosted runners only)
2. **Install System Dependencies** (cmake, build-essential, etc.)
3. **Verify Git Submodules** (C++ extension sources)
4. **Create .env File** (optional)
5. **Install SAGE** via `ci_install_wrapper.sh`
6. **Verify Installation** (imports, CLI, C++ extensions)

## Migration Guide

### Before (manual installation in each workflow)

```yaml
- name: Setup Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'

- name: Install System Dependencies
  run: |
    sudo apt-get update
    sudo apt-get install -y build-essential cmake ...

- name: Verify Submodules
  run: |
    git submodule status
    # ... lots of verification code ...

- name: Install SAGE
  run: |
    chmod +x ./quickstart.sh
    ./quickstart.sh --dev --yes

- name: Verify Installation
  run: |
    python -c "import sage"
    # ... more verification ...
```

### After (using this action)

```yaml
- name: Setup SAGE
  uses: ./.github/actions/setup-sage
  with:
    install-mode: 'dev'
```

## Supported Runners

- ✅ GitHub-hosted runners (ubuntu-latest)
- ✅ Self-hosted runners (with Python pre-installed)

The action automatically detects the runner type and adjusts accordingly.
