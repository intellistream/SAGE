# Multimodal SageDB Examples

Hands-on scripts that illustrate how to work with the multimodal wrapper that ships with SageDB. These demos rely on the Python helper `multimodal_sage_db` which transparently falls back to a pure-Python mock when the native extension is not present, so they run even if you have not compiled the C++ backend yet (performance will differ).

## Available demos

| Script | What it shows |
|--------|---------------|
| `text_image_quickstart.py` | Create a small text+image database, add samples, run fused retrieval, inspect modality stats. |
| `cross_modal_search.py` | Perform text-to-image lookups and compare results against fused retrieval, including custom fusion weights. |

Run any script from the repository root:

```bash
python examples/multimodal/text_image_quickstart.py
```

To get full performance, install the native module before running:

```bash
sage extensions install sage_db  # add --force if you need to rebuild
```
