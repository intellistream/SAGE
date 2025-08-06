"""
Main CLI entry point for SAGE Development Toolkit.

This module provides the command-line interface using Typer framework
for intuitive and powerful command-line interactions.
"""

import sys
import typer
from .commands.common import console
from .commands import get_apps

# 创建主应用
app = typer.Typer(
    name="sage-dev",
    help="🛠️ SAGE Development Toolkit - Unified development tools for SAGE project",
    no_args_is_help=True
)

# 动态添加所有命令模块的命令
def _register_commands():
    """注册所有模块化命令"""
    apps = get_apps()
    
    # 直接从各个模块注册命令到主应用
    # Core commands
    core_app = apps['core']
    for command_name, command_func in core_app.registered_commands.items():
        app.registered_commands[command_name] = command_func
    
    # Package management commands  
    package_app = apps['package_mgmt']
    for command_name, command_func in package_app.registered_commands.items():
        app.registered_commands[command_name] = command_func
    
    # Maintenance commands
    maintenance_app = apps['maintenance']
    for command_name, command_func in maintenance_app.registered_commands.items():
        app.registered_commands[command_name] = command_func
        
    # Commercial commands
    commercial_app = apps['commercial']
    for command_name, command_func in commercial_app.registered_commands.items():
        app.registered_commands[command_name] = command_func
        
    # Development commands
    development_app = apps['development']
    for command_name, command_func in development_app.registered_commands.items():
        app.registered_commands[command_name] = command_func
        
    # Reporting commands
    reporting_app = apps['reporting']
    for command_name, command_func in reporting_app.registered_commands.items():
        app.registered_commands[command_name] = command_func
        
    # Home commands
    home_app = apps['home']
    for command_name, command_func in home_app.registered_commands.items():
        app.registered_commands[command_name] = command_func

# 注册所有命令
_register_commands()


@app.callback()
def callback():
    """
    SAGE Development Toolkit - Unified development tools for SAGE project
    
    🛠️ Core Features:
    • Test execution with intelligent change detection
    • Comprehensive dependency analysis  
    • Package management across SAGE ecosystem
    • Bytecode compilation for source code protection
    • Build artifacts cleanup and management
    • Rich reporting with multiple output formats
    • Interactive and batch operation modes
    
    📖 Common Usage Examples:
    sage-dev test --mode diff           # Run tests on changed code
    sage-dev analyze --type circular    # Check for circular dependencies
    sage-dev package list               # List all SAGE packages
    sage-dev compile packages/sage-apps # Compile package to ~/.sage/dist with symlink
    sage-dev compile packages/sage-apps --no-create-symlink  # Compile without symlink
    sage-dev compile packages/sage-apps --output /tmp/build  # Compile to custom directory
    sage-dev compile packages/sage-apps --build --upload --no-dry-run  # Compile and upload
    sage-dev compile --info             # Show SAGE home directory information
    sage-dev clean --dry-run            # Preview build artifacts cleanup
    sage-dev clean --categories pycache # Clean Python cache files
    sage-dev report                     # Generate comprehensive report
    
    🔗 More info: https://github.com/intellistream/SAGE/tree/main/dev-toolkit
    """
    pass


def main():
    """Main entry point for the CLI."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!", style="yellow")
        sys.exit(0)
    except Exception as e:
        console.print(f"❌ Unexpected error: {e}", style="red")
        sys.exit(1)


if __name__ == '__main__':
    main()
