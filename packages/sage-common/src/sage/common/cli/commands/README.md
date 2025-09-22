# SAGE CLI Commands

This folder contains the organized command modules for the SAGE CLI. Each file corresponds to a specific command group.

## Command Structure

### Core Commands (Built-in)
- `version.py` - Version information
- `config.py` - Configuration management (show, init)
- `doctor.py` - System diagnostics

### Service Management Commands
- `job.py` - Job management (submit, monitor, manage jobs)
- `deploy.py` - System deployment (start, stop, monitor system)
- `jobmanager.py` - JobManager management (start, stop, restart)

### Cluster Management Commands
- `cluster.py` - Unified Ray cluster management
- `head.py` - Head node management
- `worker.py` - Worker node management

### Extension Commands
- `extensions.py` - Extension management (install C++ extensions)

## Usage

Each command file exports a `typer.Typer` app instance that is imported and registered in the main CLI application.

## Import Pattern

All commands follow this pattern:

```python
#!/usr/bin/env python3
"""
SAGE CLI [Command Name] Command
[Description]
"""

import typer

app = typer.Typer(name="[command]", help="[description]")

@app.command()
def command_function():
    """Command implementation"""
    pass
```

## File Organization

- Each command corresponds to a second-level command in the CLI
- Files are named after their command name (e.g., `job.py` for `sage job`)
- All relative imports use `..` to access parent modules (config_manager, etc.)

## Legacy Migration

The following files were moved and renamed:
- `job.py` (unchanged)
- `deploy.py` (unchanged)
- `jobmanager_controller.py` → `jobmanager.py`
- `cluster_manager.py` → `cluster.py`
- `head_manager.py` → `head.py`
- `worker_manager.py` → `worker.py`
- `extensions.py` (unchanged)

The main.py file now imports from this commands folder instead of the CLI root.
