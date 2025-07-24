# CLI User Interface Integration and Enhancement

## Issue Summary

Currently, SAGE's installation, deployment, and management functionality is scattered across multiple scripts and command entry points, making it difficult for users to have a unified and intuitive command-line experience. We need to consolidate these into a coherent CLI tool suite.

## Current State Analysis

### Existing Command Entry Points

1. **Installation & Setup**: `setup.sh`
   - Interactive setup menu
   - Docker container management
   - Conda environment setup
   - Dependencies installation
   - HuggingFace authentication

2. **Deployment & System Management**: `deployment/sage_deployment.sh`
   - System start/stop/restart
   - Ray cluster management
   - JobManager daemon management
   - Health checks and monitoring
   - Permission management
   - Log collection and diagnostics

3. **Job Management**: `sage-jm` (via `jobmanager_controller.py`)
   - Job listing and details
   - Job control (stop, monitor, watch)
   - Health checks
   - Interactive shell

### Problems with Current Approach

- **Fragmented User Experience**: Users need to remember multiple scripts and their locations
- **Inconsistent Command Patterns**: Different scripts use different argument patterns and conventions
- **Discovery Issues**: New users struggle to find the right command for their needs
- **No Unified Help System**: Help information is scattered across different tools
- **Path Dependencies**: Scripts must be run from specific directories or with full paths

## Proposed Solution: Unified SAGE CLI

### Primary Command: `sage`

Create a single entry point `sage` that consolidates all functionality:

```bash
sage <command> [subcommand] [options] [arguments]
```

### Proposed Command Structure

#### 1. Installation & Environment Management
```bash
sage install                    # Interactive installation wizard
sage install --minimal         # Minimal setup without Docker
sage install --docker          # Full Docker setup
sage install --dependencies    # Install system dependencies only
sage env setup                  # Setup Conda environment
sage env activate              # Activate SAGE environment
sage auth huggingface          # Configure HuggingFace authentication
```

#### 2. System Deployment & Management
```bash
sage deploy                     # Start entire SAGE system
sage deploy --ray-only          # Start Ray cluster only
sage deploy --daemon-only       # Start JobManager daemon only
sage stop                       # Stop entire system
sage restart                    # Restart system
sage status                     # Show system status
sage health                     # Perform health checks
sage monitor [--refresh N]     # Real-time monitoring
```

#### 3. Job Management
```bash
sage job list                   # List all jobs
sage job show <job_uuid>        # Show job details
sage job stop <job_uuid>        # Stop a specific job
sage job kill <job_uuid>        # Force kill a job
sage job pause <job_uuid>       # Pause a job (if supported)
sage job resume <job_uuid>      # Resume a paused job
sage job delete <job_uuid>      # Delete job and cleanup resources
sage job watch <job_uuid>       # Watch job in real-time
sage job logs <job_uuid>        # Show job logs
```

#### 4. CLI Tools Management
```bash
sage cli install               # Install CLI tools
sage cli uninstall             # Uninstall CLI tools
sage cli check                 # Check CLI tools status
sage cli update                # Update CLI tools
```

#### 5. System Maintenance & Diagnostics
```bash
sage diagnose                   # System diagnosis
sage logs collect [path]       # Collect system logs
sage cleanup                   # Clean temporary files
sage report [path]             # Generate system report
sage permissions fix           # Fix system permissions
sage permissions check         # Check permission status
```

#### 6. Configuration & Information
```bash
sage config show               # Show current configuration
sage config set <key> <value>  # Set configuration value
sage version                   # Show version information
sage help                      # Show help information
sage help <command>            # Show command-specific help
```

## Implementation Strategy

### Phase 1: Core Infrastructure
- [ ] Create main `sage` command entry point
- [ ] Implement command parsing and routing system
- [ ] Create unified configuration management
- [ ] Establish consistent logging and output formatting
- [ ] Set up comprehensive help system

### Phase 2: Command Migration
- [ ] Migrate installation commands from `setup.sh`
- [ ] Migrate deployment commands from `sage_deployment.sh`
- [ ] Integrate existing `sage-jm` functionality
- [ ] Create unified job management interface

### Phase 3: Enhancement Features
- [ ] Add command auto-completion (bash/zsh)
- [ ] Implement configuration file support
- [ ] Add interactive mode for complex operations
- [ ] Create command aliases for common operations
- [ ] Add progress indicators for long-running operations

### Phase 4: Advanced Features
- [ ] Plugin system for extensibility
- [ ] Remote system management capabilities
- [ ] Configuration templates and profiles
- [ ] Integration with system package managers
- [ ] Web UI integration controls

## Technical Requirements

### Installation & Distribution
- [ ] Create proper Python package structure
- [ ] Add entry point in `setup.py` for `sage` command
- [ ] Support both local development and installed package modes
- [ ] Maintain backward compatibility with existing scripts

### Command Architecture
- [ ] Use a plugin-based command system (similar to Git)
- [ ] Implement command grouping and subcommands
- [ ] Create consistent argument parsing across all commands
- [ ] Add proper error handling and user-friendly error messages

### Configuration Management
- [ ] Support multiple configuration sources (files, env vars, CLI args)
- [ ] Implement configuration validation
- [ ] Add configuration migration for version updates
- [ ] Support user and system-wide configurations

### User Experience
- [ ] Consistent output formatting (colors, tables, progress bars)
- [ ] Interactive prompts with sensible defaults
- [ ] Confirmation prompts for destructive operations
- [ ] Machine-readable output options (JSON, CSV)

## Success Criteria

1. **Unified Experience**: Users can accomplish all SAGE-related tasks through a single `sage` command
2. **Discoverability**: New users can easily find and understand available commands through help system
3. **Consistency**: All commands follow the same patterns for arguments, options, and output
4. **Backward Compatibility**: Existing scripts and workflows continue to work during transition
5. **Documentation**: Comprehensive help available at every level of the command hierarchy

## Migration Plan

1. **Parallel Implementation**: Build new CLI alongside existing scripts
2. **Gradual Migration**: Move functionality one command group at a time
3. **Deprecation Notices**: Add warnings to old scripts directing users to new commands
4. **Documentation Updates**: Update all documentation to reference new CLI
5. **Complete Transition**: Remove old scripts after ensuring full feature parity

## Related Files

- `setup.sh` - Installation and environment setup
- `deployment/sage_deployment.sh` - System deployment and management
- `deployment/scripts/cli_manager.sh` - CLI tools management
- `deployment/jobmanager_controller.py` - Job management controller
- `setup.py` - Python package configuration

## Priority

**High** - This enhancement is crucial for improving user experience and making SAGE more accessible to new users and easier to manage for existing users.
