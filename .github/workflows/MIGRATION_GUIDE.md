# CI/CD Workflow Migration Guide - Configuration Refactor

## 🎯 Overview

This document outlines changes needed in all CI/CD workflows after the **configuration architecture refactor** (2025-12-28).

## 🔄 Key Changes

### 1. **sage llm serve** is DEPRECATED

**❌ Old way (FORBIDDEN in CI):**
```yaml
- name: Start LLM service
  run: |
    sage llm serve -m Qwen/Qwen2.5-7B-Instruct
```

**✅ New way (Control Plane):**
```yaml
- name: Start LLM service via Control Plane
  run: |
    sage llm engine start Qwen/Qwen2.5-7B-Instruct --engine-kind llm
```

### 2. Configuration Priority: CLI > config.yaml > Defaults

**Old behavior:**
- `sage llm serve` used hardcoded model `Qwen2.5-0.5B-Instruct` on port `8901`

**New behavior:**
- Reads from `config/config.yaml` first
- CLI parameters override config file
- Shows configuration being used

**CI/CD impact:**
```yaml
# Option 1: Use config.yaml defaults (recommended for tests)
- run: sage llm engine start $(yq '.llm.model' config/config.yaml) --engine-kind llm

# Option 2: Override with CLI (for specific tests)
- run: sage llm engine start Qwen/Qwen2.5-0.5B-Instruct --engine-kind llm
```

### 3. Gateway /v1/models API Enhanced

**Old behavior:**
- Returned empty list if Control Plane had no engines

**New behavior:**
- Returns online engines (from Control Plane) + offline models (from models.json)
- Each model has `status: "online"/"offline"` field
- Includes metadata (description, category, tags, size)

**CI/CD testing:**
```yaml
- name: Verify Gateway API
  run: |
    response=$(curl -s http://localhost:8888/v1/models)  # allow-control-plane-bypass: Gateway port
    echo "$response" | jq '.data | length'  # Should return > 0
    echo "$response" | jq '.data[0].status'  # Should be "online" or "offline"
```

### 4. models.json Format Changed

**Old format (DEPRECATED):**
```json
[
  {
    "name": "Qwen/Qwen2.5-7B-Instruct",
    "base_url": "http://127.0.0.1:8001/v1",  // ❌ Removed
    "default": true,                         // ❌ Removed
    "is_local": true                         // ❌ Removed
  }
]
```

**New format:**
```json
{
  "models": [
    {
      "name": "Qwen/Qwen2.5-7B-Instruct",
      "description": "标准模型",
      "category": "general",
      "size": "7B",
      "tags": ["recommended"]
    }
  ]
}
```

**CI/CD validation:**
```yaml
- name: Validate models.json format
  run: |
    python3 << 'EOF'
    import json
    from pathlib import Path

    data = json.loads(Path("config/models.json").read_text())
    assert isinstance(data, dict), "models.json must be a dict"
    assert "models" in data, "models.json must have 'models' key"

    for model in data["models"]:
        # These fields should NOT exist
        assert "base_url" not in model, f"{model['name']} has forbidden base_url"
        assert "port" not in model, f"{model['name']} has forbidden port"
        assert "default" not in model, f"{model['name']} has forbidden default"
        assert "is_local" not in model, f"{model['name']} has forbidden is_local"

    print("✅ models.json format is valid")
    EOF
```

## 📋 Workflows to Update

### Priority 1: Core Testing Workflows

1. **build-test.yml** - Main test suite
   - [ ] Replace `sage llm serve` with `sage llm engine start`
   - [ ] Add config.yaml validation
   - [ ] Add models.json format check

2. **examples-test.yml** - Examples validation
   - [ ] Update example scripts to use Control Plane
   - [ ] Verify examples don't use `sage llm serve`

3. **code-quality.yml** - Linting and formatting
   - [ ] Already includes pre-commit hooks (will catch violations)
   - [ ] No changes needed

4. **installation-test.yml** - Package installation
   - [ ] Test config.yaml is included in package
   - [ ] Test models.json is included

### Priority 2: Deployment Workflows

5. **publish-pypi.yml** - PyPI publishing
   - [ ] Ensure new config files are in MANIFEST.in

6. **deploy-studio.yml** - Studio deployment
   - [ ] Studio frontend should use Gateway API for model list
   - [ ] No direct vLLM service startup

### Priority 3: Experiment Workflows

7. **paper1-experiments.yml** - GPU experiments
   - [ ] Use Control Plane for all LLM operations
   - [ ] Update result collection to use Gateway API

## 🔧 Example Workflow Updates

### Before (❌ Old):
```yaml
name: Test
jobs:
  test:
    steps:
      - name: Start services
        run: |
          sage llm serve -m Qwen/Qwen2.5-0.5B-Instruct -p 8901

      - name: Run tests
        run: pytest
```

### After (✅ New):
```yaml
name: Test
jobs:
  test:
    steps:
      - name: Start Gateway
        run: sage gateway start

      - name: Start LLM via Control Plane
        run: |
          # Use config.yaml default or override with CLI
          sage llm engine start Qwen/Qwen2.5-0.5B-Instruct --engine-kind llm

      - name: Verify engine status
        run: |
          sage llm engine list
          curl -s http://localhost:8888/v1/models | jq '.data | length'  # allow-control-plane-bypass: Gateway port

      - name: Run tests
        run: pytest
```

## 🚨 Pre-commit Hook Enforcement

The `control-plane-only-guard` pre-commit hook will now catch:

1. ❌ Direct vLLM imports: `from vllm import LLM`
2. ❌ Direct API server: `python -m vllm.entrypoints.openai.api_server`
3. ❌ Bypassing Control Plane: `sage llm serve`
4. ❌ Hardcoded ports: `localhost:8001`, `localhost:8901`

**Allowed files** (framework internals):
- `packages/sage-llm-core/src/sage/llm/api_server.py`
- `packages/sage-cli/src/sage/cli/commands/apps/llm.py`
- `docs-public/` (documentation)

## 📝 Validation Checklist

Before committing workflow changes:

- [ ] No `sage llm serve` commands
- [ ] All LLM operations via `sage llm engine start`
- [ ] Gateway is started before engines
- [ ] Tests verify Gateway /v1/models API
- [ ] Config files are validated
- [ ] Pre-commit hooks pass

## 🔗 References

- [Configuration Architecture](../../config/README.md)
- [Control Plane Documentation](../../docs-public/docs_src/dev-notes/l1-common/control-plane.md)
- [Copilot Instructions](../.github/copilot-instructions.md)

---

**Last Updated:** 2025-12-28  
**Status:** 🚧 Migration in progress
