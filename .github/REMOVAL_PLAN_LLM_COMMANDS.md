# Removal Plan: Direct LLM Service Commands

## 🎯 Objective

**Enforce 100% Control Plane architecture** by removing ALL commands that bypass Control Plane.

## ❌ Commands to Remove

### 1. `sage llm serve` (Line ~988-1168)
**Why**: Directly starts vLLM bypassing Control Plane  
**Replacement**: `sage llm engine start <model> --engine-kind llm`

### 2. `sage llm run` (Line ~839-903)
**Why**: Blocking mode that bypasses Control Plane  
**Replacement**: `sage llm engine start` (Control Plane manages lifecycle)

### 3. `sage llm stop` (Line ~1169-1182)
**Why**: Manages services started by `sage llm serve`  
**Replacement**: `sage llm engine stop <engine-id>`

### 4. `sage llm restart` (Line ~1183-1219)
**Why**: Restarts services started by `sage llm serve`  
**Replacement**: `sage llm engine stop` + `sage llm engine start`

### 5. `sage llm status` (Line ~1220-1352)
**Why**: Shows status of directly-started services  
**Replacement**: `sage llm engine list`

### 6. `sage llm logs` (Line ~1353-end)
**Why**: Shows logs of directly-started services  
**Replacement**: `sage gateway logs` or engine-specific logs

### 7. Helper Functions to Remove
- `_get_default_llm_config()` (Line ~945-973)
- `_get_default_embedding_config()` (Line ~976-986)

These were added for `sage llm serve` config loading.

## ✅ Commands to KEEP

### Core Commands (use Control Plane)
- `sage llm gpu` - GPU info utility (doesn't start services)
- `sage llm fine-tune` - Model fine-tuning (separate concern)

### Model Management
- All `sage llm model *` commands (subcommand)

### Engine Management (Control Plane)
- All `sage llm engine *` commands (subcommand)

### Preset Management
- All `sage llm preset *` commands (subcommand)

## 📋 Implementation Steps

1. **Delete Functions** (Lines 945-end of service commands)
   - Remove `serve_llm()`
   - Remove `stop_llm()`
   - Remove `restart_llm()`
   - Remove `status_llm()`
   - Remove `logs_llm()`
   - Remove `_get_default_llm_config()`
   - Remove `_get_default_embedding_config()`

2. **Update Imports**
   - Remove unused `LLMLauncher` import if no longer needed
   - Keep `LLMServerConfig` for engine commands

3. **Add Deprecation Notice**
   - Add command that shows migration guide

4. **Update Documentation**
   - Search and replace all `sage llm serve` → `sage llm engine start`
   - Update examples, README, tutorials

5. **Update Tests**
   - Update test files using `sage llm serve`
   - CI/CD workflows

## 🔍 Files to Search & Update

```bash
# Find all references to removed commands
rg "sage llm serve" --type md --type py --type yaml
rg "sage llm run" --type md --type py --type yaml
rg "sage llm stop" --type md --type py --type yaml
rg "sage llm status" --type md --type py --type yaml
```

## 💡 Migration Message

When user tries deleted commands, show:

```
❌ This command has been removed to enforce Control Plane architecture.

✅ Use Control Plane instead:

  Old: sage llm serve -m Qwen/Qwen2.5-7B-Instruct
  New: sage llm engine start Qwen/Qwen2.5-7B-Instruct --engine-kind llm

  Old: sage llm status
  New: sage llm engine list

  Old: sage llm stop
  New: sage llm engine stop <engine-id>

📚 See: docs/dev-notes/l1-common/control-plane.md
```

## ✅ Validation Checklist

- [ ] All removed commands deleted from llm.py
- [ ] No broken imports
- [ ] `sage llm --help` shows only Control Plane commands
- [ ] Documentation updated
- [ ] Examples updated
- [ ] CI/CD workflows updated
- [ ] Pre-commit hook catches violations
- [ ] Tests pass

---

**Date**: 2025-12-28  
**Branch**: feature/intent-refactor  
**Impact**: Breaking change - requires migration guide
