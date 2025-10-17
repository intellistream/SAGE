# Agent Tutorials - Data Files

This directory contains sample data for agent tutorials.

## Files

- **`agent_queries.jsonl`** - Standard agent queries for testing
- **`agent_queries_test.jsonl`** - Test queries for agent examples

## Format

Each line in the JSONL file contains a query object:

```json
{"query": "Your question here", "metadata": {...}}
```

## Usage

These files are referenced in:
- `../basic_agent.py`
- `../config/config_agent_min.yaml`

## Custom Queries

Add your own queries to test different agent behaviors.
