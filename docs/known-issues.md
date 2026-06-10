# Known Issues

This document tracks known limitations in SAGE's downstream dependencies that
may affect deployment, performance, or feature availability.

---

## Inference Engine (vLLM-Ascend)

### Speculative Decoding is Fundamentally Unsupported

**Affected component:** `vllm-ascend-hust` (Ascend NPU inference backend)

**Summary:**
Speculative decoding is **not functional** in the current vllm-ascend build.
Multiple methods have been tested and all fail at runtime:

- **Draft model speculation:** `AscendDraftModelProposer` does not implement
  `update_stream` — crashes at runtime.
- **Ngram-based speculation:** Also crashes on Ascend despite running on CPU.
  The interaction with the Ascend verification path is broken.

This is not a single-method limitation but a fundamental incompatibility in
the current build. **Do not enable any `speculative_config` on Ascend.**

**Recommended configuration (no speculation):**

Revert to a standard non-speculative serving config:

```bash
# Do NOT pass --speculative-config or speculative_config to the engine.
# Run the target model directly without speculation.
vllm serve <model> --tensor-parallel-size <N> ...
```

**EAGLE-based methods** (EAGLE / EAGLE-3 / MTP) have a separate Ascend-native
code path (`AscendEagleProposer`) and *may* still work, but have not been
validated in our deployment. Use at your own risk.

**Detailed documentation:**

- Feature guide: `vllm-ascend-hust/docs/source/user_guide/feature_guide/speculative_decoding.md`
- Suffix Decoding tutorial: `vllm-ascend-hust/docs/source/tutorials/features/suffix_speculative_decoding.md`

**Status:** Open — speculative decoding fundamentally broken in current build.
**Last verified:** 2026-06-05.

---

## Adding New Entries

When documenting a new known issue, include:

1. **Affected component** — which downstream package or service is involved.
2. **Summary** — concise description of the limitation.
3. **Workaround** — actionable steps or configuration to mitigate.
4. **Detailed documentation** — links/paths to authoritative references.
5. **Status** — Open / Resolved (with version).
