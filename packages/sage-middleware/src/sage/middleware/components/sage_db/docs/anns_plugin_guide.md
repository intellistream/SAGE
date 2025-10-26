# ANNS Plugin Interface

This document describes the pluggable Approximate Nearest Neighbor Search (ANNS) layer that powers
`sage_db`. The new architecture is inspired by
[big-ann-benchmarks](https://github.com/erikbern/ann-benchmarks) and lets you integrate new search
algorithms without modifying the core database code.

## Core abstractions

All ANNS integrations live under `include/sage_db/anns` and `src/anns`.

### `ANNSAlgorithm`

`ANNSAlgorithm` is the base interface that every backend must implement. It exposes:

- identity: `name()`, `version()`, and `description()`
- capability introspection: supported metrics, online updates, deletions, range-search support
- lifecycle hooks: `fit()`, `save()`, `load()`, `is_built()`
- query entry points: single query, batch query, and optional range query
- dynamic index maintenance: `add_vector(s)`, `remove_vector(s)` (throw if unsupported)
- statistics & configuration helpers

All vectors are handled as `(VectorId, Vector)` pairs (`VectorEntry`) so algorithms have access to
the original IDs during builds and updates.

### `ANNSFactory` & `ANNSRegistry`

Algorithms register with the singleton `ANNSRegistry`. Each factory returns:

- `create()` – constructs a fresh algorithm instance
- default build/query parameter templates
- metadata describing the algorithm and supported metrics

Registration is one line thanks to the helper macro:

```cpp
REGISTER_ANNS_ALGORITHM(MyAlgorithmFactory);
```

(To avoid static-initialization surprises, perform registration in a `.cpp` file.)

### Parameters

`AlgorithmParams` and `QueryConfig` provide typed key/value stores. They already mirror big-ann's
style so you can pass arbitrary algorithm-specific options without changing the interface.

## Shipping algorithms

The refactor ships with two backends:

1. **`brute_force`** – new reference implementation used as the default backend. It supports
   incremental updates and deletions and is always available.
1. **`faiss` (placeholder)** – header scaffold for wiring FAISS into the new API. Implementations
   can live in `faiss_plugin.{h,cpp}` without touching the rest of the system.

Adding another backend only requires:

1. Implementing `ANNSAlgorithm` + `ANNSFactory` in `include/sage_db/anns/<name>_plugin.h` and
   `src/anns/<name>_plugin.cpp`.
1. Registering via `REGISTER_ANNS_ALGORITHM`.
1. (Optional) extending the build to pull in extra dependencies.

`VectorStore` now consumes `ANNSRegistry` instead of the raw FAISS API, so the rest of the database
is oblivious to the concrete implementation.

## Selecting algorithms

`DatabaseConfig` introduces three new knobs:

```cpp
struct DatabaseConfig {
    std::string anns_algorithm = "brute_force";
    std::unordered_map<std::string, std::string> anns_build_params;
    std::unordered_map<std::string, std::string> anns_query_params;
};
```

You can specify them directly or tweak them at runtime (Python bindings expose the fields as plain
dictionaries).

If `anns_algorithm` is empty or `"auto"`, `brute_force` is selected. When a backend is absent the
registry automatically falls back to `brute_force` as well.

## Persistence semantics

`VectorStore` persists:

- raw dataset (`*.vectors`)
- optional backend index (`*.vectors.anns`) if a trained index is available

During load we prefer the saved index when its size matches the logical dataset; otherwise we
rebuild automatically using the stored vectors. This guarantees correctness even if the plugin
declines to implement persistence.

## Quick start for new backends

1. Copy `brute_force_plugin.{h,cpp}` as a template.
1. Replace the distance computations and build/query paths.
1. Expose algorithm-specific parameters through `AlgorithmParams` / `QueryConfig`.
1. Update `CMakeLists.txt` to compile the new sources and link additional libraries.

With this structure you can prototype ANNS integration locally and share the plugin with the rest of
the team without coordinating changes to the main database engine.
