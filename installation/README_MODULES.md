# SAGE Installation Module Documentation

## Overview

The SAGE installation system has been refactored into a modular architecture for better maintainability, testability, and separation of concerns. The complex monolithic `install.py` file has been broken down into focused modules, each handling specific aspects of the installation process.

## Module Architecture

### Core Modules

Located in `/installation/modules/`:

#### 1. `base.py` - Foundation Module
- **Purpose**: Common utilities and base functionality
- **Key Components**:
  - `Colors` class for terminal formatting
  - `BaseInstaller` base class with shared methods
  - Common utilities (command execution, user input, configuration management)

#### 2. `system_manager.py` - System Dependencies
- **Purpose**: Handle system-level dependencies and platform detection
- **Key Functions**:
  - Check for conda/docker installation
  - Install system dependencies (build-essential, cmake, etc.)
  - Platform-specific package manager detection (apt, yum, dnf)

#### 3. `conda_manager.py` - Conda Environment Management
- **Purpose**: Manage conda environments and Python packages
- **Key Functions**:
  - Create/remove conda environments
  - Install Python packages
  - Hugging Face authentication setup
  - Environment validation

#### 4. `docker_manager.py` - Docker Operations
- **Purpose**: Handle Docker container operations
- **Key Functions**:
  - Pull Docker images
  - Start/stop containers
  - Container dependency installation
  - Docker-specific conda environment setup

#### 5. `package_manager.py` - Package Installation
- **Purpose**: Handle SAGE package installation and C++ extensions
- **Key Functions**:
  - Build C++ extensions (sage_ext)
  - Install SAGE packages (minimal/full modes)
  - Third-party component installation (Kafka)
  - Build artifact cleanup
  - Activation script generation

#### 6. `menu_handler.py` - User Interface
- **Purpose**: Handle interactive menus and user interactions
- **Key Functions**:
  - Main menu display
  - Status reporting
  - Help and troubleshooting information
  - Example script execution
  - User input validation

#### 7. `sage_installer.py` - Main Orchestrator
- **Purpose**: Coordinate all modules for complete installation workflows
- **Key Functions**:
  - Minimal setup orchestration
  - Full setup orchestration
  - Uninstallation process
  - Configuration management across modules

## Benefits of Modular Architecture

### 1. **Separation of Concerns**
- Each module has a single, well-defined responsibility
- System dependencies are separate from package management
- Docker operations are isolated from conda management

### 2. **Improved Maintainability**
- Smaller, focused files are easier to understand and modify
- Changes to one component don't affect others
- Clear interfaces between modules

### 3. **Better Testing**
- Individual modules can be unit tested independently
- Mock dependencies easily for testing
- Isolated testing of specific functionality

### 4. **Code Reusability**
- Modules can be reused in different contexts
- Common functionality is centralized in base classes
- Easy to extend with new installation methods

### 5. **Easier Debugging**
- Errors are localized to specific modules
- Clearer stack traces
- Easier to identify which component is failing

## Usage Examples

### Using Individual Modules

```python
from installation.modules import SystemManager, CondaManager

# Check system dependencies
sys_mgr = SystemManager()
if sys_mgr.check_conda_installed():
    print("Conda is available")

# Manage conda environment
conda_mgr = CondaManager("my-sage-env")
conda_mgr.create_conda_environment()
conda_mgr.install_python_packages(minimal=True)
```

### Using the Main Installer

```python
from installation.modules import SageInstaller

installer = SageInstaller("custom-env-name")
installer.minimal_setup()  # Complete minimal installation
```

## File Structure

```
installation/
├── modules/
│   ├── __init__.py              # Module exports
│   ├── base.py                  # Base classes and utilities
│   ├── system_manager.py        # System dependencies
│   ├── conda_manager.py         # Conda environment management
│   ├── docker_manager.py        # Docker operations
│   ├── package_manager.py       # Package installation
│   ├── menu_handler.py          # User interface
│   └── sage_installer.py        # Main orchestrator
├── container_setup/             # Docker-related scripts
├── env_setup/                   # Environment setup scripts
└── kafka_setup/                 # Kafka installation scripts

install_new.py                    # New simplified entry point
install.py                        # Original monolithic script (to be replaced)
```

## Migration Guide

### For End Users
- The installation experience remains the same
- All existing command-line options are preserved
- `python install.py` continues to work as before

### For Developers
- Import from `installation.modules` instead of the monolithic file
- Use specific managers for targeted functionality
- Extend by creating new modules following the same pattern

### Replacing the Old System
1. Test the new modular system thoroughly
2. Update any external scripts that import from `install.py`
3. Replace `install.py` with `install_new.py`
4. Update documentation and CI/CD scripts

## Extension Points

### Adding New Installation Methods
1. Create a new module in `installation/modules/`
2. Inherit from `BaseInstaller`
3. Add the module to `sage_installer.py` orchestration
4. Export in `__init__.py`

### Adding New Platforms
1. Extend `SystemManager` with platform detection
2. Add platform-specific dependency installation
3. Update documentation

### Adding New Components
1. Extend `PackageManager` with new component logic
2. Add UI elements in `MenuHandler`
3. Update help documentation

## Testing Strategy

### Unit Tests
- Test each module independently
- Mock external dependencies (conda, docker, etc.)
- Validate configuration management

### Integration Tests
- Test module interactions
- Test complete installation workflows
- Validate error handling across modules

### End-to-End Tests
- Test complete installation scenarios
- Validate cleanup and uninstallation
- Test various platform configurations

## Configuration Management

All modules share a common configuration system:
- Configuration is stored in `~/.sage/config.json`
- Modules sync configuration through the base installer
- Configuration includes setup type, environment names, Docker containers, etc.

This modular approach provides a solid foundation for the SAGE installation system while maintaining backward compatibility and improving the developer experience.
