"""
Main CLI entry point for SAGE Development Toolkit.

This module provides the command-line interface using Click framework
for intuitive and powerful command-line interactions.
"""

import sys
import click
from pathlib import Path
from typing import Optional

from ..core.toolkit import SAGEDevToolkit
from ..core.exceptions import SAGEDevToolkitError


@click.group()
@click.option(
    '--project-root',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help='Project root directory path'
)
@click.option(
    '--config',
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help='Configuration file path'
)
@click.option(
    '--environment',
    type=click.Choice(['development', 'production', 'ci']),
    help='Environment configuration to use'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose logging'
)
@click.pass_context
def cli(ctx, project_root: Optional[Path], config: Optional[Path], 
        environment: Optional[str], verbose: bool):
    """SAGE Development Toolkit - Unified development tools for SAGE project."""
    
    # Ensure the context object exists
    ctx.ensure_object(dict)
    
    try:
        # Initialize toolkit
        toolkit = SAGEDevToolkit(
            project_root=str(project_root) if project_root else None,
            config_file=str(config) if config else None,
            environment=environment
        )
        
        # Store toolkit in context for subcommands
        ctx.obj['toolkit'] = toolkit
        ctx.obj['verbose'] = verbose
        
        if verbose:
            click.echo(f"✅ Toolkit initialized for environment: {toolkit.config.environment}")
            click.echo(f"📁 Project root: {toolkit.config.project_root}")
            click.echo(f"🔧 Available tools: {', '.join(toolkit.tools.keys())}")
            
    except SAGEDevToolkitError as e:
        click.echo(f"❌ Error initializing toolkit: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--mode', type=click.Choice(['all', 'diff', 'package']), default='diff',
              help='Test execution mode')
@click.option('--package', help='Package name for package mode')
@click.option('--workers', type=int, help='Number of parallel workers')
@click.option('--timeout', type=int, help='Test timeout in seconds')
@click.option('--quick', is_flag=True, help='Run quick tests only')
@click.pass_context
def test(ctx, mode: str, package: Optional[str], workers: Optional[int], 
         timeout: Optional[int], quick: bool):
    """Run tests with various modes and options."""
    toolkit = ctx.obj['toolkit']
    verbose = ctx.obj['verbose']
    
    try:
        kwargs = {}
        if package:
            kwargs['package'] = package
        if workers:
            kwargs['workers'] = workers
        if timeout:
            kwargs['timeout'] = timeout
        if quick:
            kwargs['quick'] = quick
            
        if verbose:
            click.echo(f"🧪 Running tests in '{mode}' mode...")
            
        results = toolkit.run_tests(mode, **kwargs)
        
        # Display summary
        if 'summary' in results:
            summary = results['summary']
            click.echo(f"✅ Tests completed:")
            click.echo(f"  - Total: {summary.get('total', 0)}")
            click.echo(f"  - Passed: {summary.get('passed', 0)}")
            click.echo(f"  - Failed: {summary.get('failed', 0)}")
            click.echo(f"  - Duration: {results.get('execution_time', 0):.2f}s")
        else:
            click.echo("✅ Tests completed successfully")
            
    except SAGEDevToolkitError as e:
        click.echo(f"❌ Test execution failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--type', 'analysis_type', 
              type=click.Choice(['full', 'summary', 'circular']), 
              default='summary',
              help='Type of dependency analysis')
@click.pass_context
def analyze(ctx, analysis_type: str):
    """Analyze project dependencies."""
    toolkit = ctx.obj['toolkit']
    verbose = ctx.obj['verbose']
    
    try:
        if verbose:
            click.echo(f"🔍 Running dependency analysis: {analysis_type}")
            
        results = toolkit.analyze_dependencies(analysis_type)
        
        # Display summary
        if analysis_type == 'circular':
            circular_deps = results.get('circular_dependencies', [])
            if circular_deps:
                click.echo("⚠️  Circular dependencies found:")
                for dep in circular_deps[:5]:  # Show first 5
                    click.echo(f"  - {' -> '.join(dep)}")
                if len(circular_deps) > 5:
                    click.echo(f"  ... and {len(circular_deps) - 5} more")
            else:
                click.echo("✅ No circular dependencies found")
        else:
            click.echo("✅ Dependency analysis completed")
            click.echo(f"  - Analysis time: {results.get('execution_time', 0):.2f}s")
            
    except SAGEDevToolkitError as e:
        click.echo(f"❌ Dependency analysis failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('action', type=click.Choice(['list', 'install', 'uninstall', 'status', 'build']))
@click.argument('package_name', required=False)
@click.option('--dev', is_flag=True, help='Install in development mode')
@click.option('--force', is_flag=True, help='Force operation')
@click.pass_context
def package(ctx, action: str, package_name: Optional[str], dev: bool, force: bool):
    """Manage SAGE packages."""
    toolkit = ctx.obj['toolkit']
    verbose = ctx.obj['verbose']
    
    try:
        kwargs = {}
        if dev:
            kwargs['dev'] = dev
        if force:
            kwargs['force'] = force
            
        if verbose:
            click.echo(f"📦 Package management: {action}")
            
        results = toolkit.manage_packages(action, package_name, **kwargs)
        
        # Display results based on action
        if action == 'list':
            packages = results.get('packages', [])
            click.echo(f"📦 Found {len(packages)} packages:")
            for pkg in packages:
                status = "✅" if pkg.get('installed') else "❌"
                click.echo(f"  {status} {pkg.get('name', 'Unknown')}")
        elif action == 'status':
            click.echo("📦 Package status:")
            for key, value in results.items():
                click.echo(f"  - {key}: {value}")
        else:
            click.echo(f"✅ Package {action} completed successfully")
            
    except SAGEDevToolkitError as e:
        click.echo(f"❌ Package management failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--format', 'output_format', 
              type=click.Choice(['json', 'markdown', 'both']), 
              default='both',
              help='Output format for report')
@click.pass_context
def report(ctx, output_format: str):
    """Generate comprehensive development report."""
    toolkit = ctx.obj['toolkit']
    verbose = ctx.obj['verbose']
    
    try:
        if verbose:
            click.echo("📊 Generating comprehensive report...")
            
        results = toolkit.generate_comprehensive_report()
        
        # Display summary
        sections = results.get('sections', {})
        click.echo("📊 Report generated successfully:")
        
        for section_name, section_data in sections.items():
            status = section_data.get('status', 'unknown')
            icon = "✅" if status == "success" else "❌" if status == "error" else "⚠️"
            section_title = section_name.replace('_', ' ').title()
            click.echo(f"  {icon} {section_title}")
            
        execution_time = results.get('metadata', {}).get('execution_time', 0)
        click.echo(f"⏱️  Report generation time: {execution_time:.2f}s")
            
    except SAGEDevToolkitError as e:
        click.echo(f"❌ Report generation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def interactive(ctx):
    """Enter interactive mode."""
    toolkit = ctx.obj['toolkit']
    
    click.echo("🚀 SAGE Development Toolkit - Interactive Mode")
    click.echo("Type 'help' for available commands, 'exit' to quit")
    
    while True:
        try:
            command = click.prompt("\nSAGE-DEV", default="", show_default=False)
            command = command.strip()
            
            if not command:
                continue
                
            if command in ('exit', 'quit', 'q'):
                click.echo("👋 Goodbye!")
                break
                
            elif command == 'help':
                click.echo("Available commands:")
                click.echo("  test [mode]           - Run tests")
                click.echo("  analyze [type]        - Analyze dependencies")
                click.echo("  package list          - List packages")
                click.echo("  package status        - Package status")
                click.echo("  report                - Generate report")
                click.echo("  status                - Show toolkit status")
                click.echo("  exit/quit/q           - Exit interactive mode")
                
            elif command.startswith('test'):
                parts = command.split()
                mode = parts[1] if len(parts) > 1 else 'diff'
                try:
                    results = toolkit.run_tests(mode)
                    click.echo("✅ Tests completed")
                except Exception as e:
                    click.echo(f"❌ Test failed: {e}")
                    
            elif command.startswith('analyze'):
                parts = command.split()
                analysis_type = parts[1] if len(parts) > 1 else 'summary'
                try:
                    results = toolkit.analyze_dependencies(analysis_type)
                    click.echo("✅ Analysis completed")
                except Exception as e:
                    click.echo(f"❌ Analysis failed: {e}")
                    
            elif command == 'package list':
                try:
                    results = toolkit.manage_packages('list')
                    packages = results.get('packages', [])
                    click.echo(f"📦 {len(packages)} packages found")
                except Exception as e:
                    click.echo(f"❌ Package listing failed: {e}")
                    
            elif command == 'package status':
                try:
                    results = toolkit.manage_packages('status')
                    click.echo("📦 Package status retrieved")
                except Exception as e:
                    click.echo(f"❌ Status check failed: {e}")
                    
            elif command == 'report':
                try:
                    results = toolkit.generate_comprehensive_report()
                    click.echo("📊 Report generated")
                except Exception as e:
                    click.echo(f"❌ Report generation failed: {e}")
                    
            elif command == 'status':
                status = toolkit.get_tool_status()
                click.echo(f"🔧 Loaded tools: {', '.join(status['loaded_tools'])}")
                
            else:
                click.echo(f"❓ Unknown command: {command}. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            click.echo("\n👋 Goodbye!")
            break
        except EOFError:
            click.echo("\n👋 Goodbye!")
            break
        except Exception as e:
            click.echo(f"❌ Error: {e}")


@cli.command()
@click.pass_context
def status(ctx):
    """Show toolkit status and configuration."""
    toolkit = ctx.obj['toolkit']
    
    click.echo("🔧 SAGE Development Toolkit Status")
    click.echo(f"📁 Project root: {toolkit.config.project_root}")
    click.echo(f"🌍 Environment: {toolkit.config.environment}")
    
    status_info = toolkit.get_tool_status()
    loaded_tools = status_info['loaded_tools']
    available_tools = status_info['available_tools']
    
    click.echo(f"🛠️  Tools: {len(loaded_tools)}/{len(available_tools)} loaded")
    for tool in available_tools:
        icon = "✅" if tool in loaded_tools else "❌"
        click.echo(f"  {icon} {tool}")
    
    # Validate configuration
    errors = toolkit.validate_configuration()
    if errors:
        click.echo("⚠️  Configuration issues:")
        for error in errors:
            click.echo(f"  - {error}")
    else:
        click.echo("✅ Configuration is valid")


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()
