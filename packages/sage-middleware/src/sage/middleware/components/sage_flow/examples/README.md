# Sage Flow Python Examples

This directory hosts lightweight examples that show how to drive the
`sage_flow` runtime from Python. They are intended for developers who
install or develop SAGE locally and want a quick sanity check that the
C++ extension and Python bindings were built correctly.

## Prerequisites

1. Build the SageFlow C++ extension (for example, via `sage extensions install sage_flow`
   or by configuring the superbuild in `packages/sage-middleware`).
2. Make sure the `sage-middleware` package (or the repository root) is on
   your `PYTHONPATH`, e.g.:

   ```bash
   python -m pip install -e packages/sage-middleware
   ```

3. Activate the same Python environment that was used for the build so
   the `_sage_flow` shared library can be imported.

## Available examples

- `basic_service.py` – feeds random vectors into `SageFlowService`,
  attaches a simple Python sink, and executes the pipeline once.

Run an example with:

```bash
python -m sage.middleware.components.sage_flow.examples.basic_service
```

The script will exit early with a helpful message if the underlying
`_sage_flow` extension is missing.
