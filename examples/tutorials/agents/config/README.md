# Agent Tutorials - Configuration

This directory contains configuration files for agent tutorials.

## Files

- **`config_agent_min.yaml`** - Minimal agent configuration

## Usage

Referenced by `../basic_agent.py`:

```python
cfg_path = os.path.join(
    os.path.dirname(__file__), "config", "config_agent_min.yaml"
)
```

## Customization

Modify the config file to change:
- LLM model
- Agent tools
- Data sources
- Behavior parameters
