# Pull Request

## Summary

- What changed:
- Why:

## Scope

- In scope:
- Out of scope:

## Boundary & Dependency Checklist (Mandatory)

- [ ] Change preserves strict layer direction: `L4 -> L3 -> L2 -> L1`
- [ ] No compatibility shim / re-export / fallback added
- [ ] Capability ownership is explicit for independent sub-repos (including `sagellm`); no in-repo re-embedding
- [ ] If touching capability families (`neuromem`/`sageVDB`/`sageFlownet`/`sagellm`), ownership and rollout order are explicitly stated
- [ ] Algorithm-only contracts remain separate from runtime/service-bound implementation
- [ ] No new `ray` import/dependency (Flownet-first)
- [ ] Any dependency addition is necessary for current layer responsibilities

## No-Compatibility-Layer Self-Check (Mandatory)

- [ ] No dual-path import pattern (`try new_path -> except old_path`)
- [ ] No compatibility alias wrappers kept for migration convenience
- [ ] Call sites are updated directly to canonical import path
- [ ] On missing dependency/path, behavior is fail-fast (no silent fallback)

## Evidence

- Related issue(s):
- Code paths touched:
- Verification commands and key output:

## Risk & Rollback

- Risk:
- Rollback plan:
