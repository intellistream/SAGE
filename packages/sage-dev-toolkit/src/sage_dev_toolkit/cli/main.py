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
    
    # 从各个模块添加命令到主应用
    for app_name, sub_app in apps.items():
        # 将子应用的所有命令添加到主应用
        for command_info in sub_app.registered_commands:
            app.registered_commands.append(command_info)

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
    • PyPI package upload and publishing
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
    sage-dev pypi list                  # List all available packages for PyPI upload
    sage-dev pypi build                 # Build all open-source packages
    sage-dev pypi upload --no-dry-run   # Upload all open-source packages to PyPI
    sage-dev pypi upload pkg1,pkg2 -t   # Upload specific packages to TestPyPI
    sage-dev pypi check                 # Check package configurations and build artifacts
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
