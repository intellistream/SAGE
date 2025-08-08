"""
Core commands for SAGE Development Toolkit.

Includes: test, analyze, status, version commands.
"""

from typing import Optional

import typer
from rich.table import Table
from rich.panel import Panel

from .common import (
    console, get_toolkit, handle_command_error,
    PROJECT_ROOT_OPTION, CONFIG_OPTION, ENVIRONMENT_OPTION, VERBOSE_OPTION
)

app = typer.Typer(name="core", help="Core SAGE development commands")


@app.command("test")
def test_command(
    mode: str = typer.Option("diff", help="Test execution mode: all, diff, package, failed"),
    package: Optional[str] = typer.Option(None, help="Package name for package mode"),
    workers: Optional[int] = typer.Option(None, help="Number of parallel workers"),
    timeout: Optional[int] = typer.Option(None, help="Test timeout in seconds"),
    quick: bool = typer.Option(False, help="Run quick tests only"),
    enable_coverage: bool = typer.Option(False, "--enable-coverage", help="Enable coverage reporting"),
    show_details: bool = typer.Option(False, "--show-details", help="Show detailed test report with individual file results"),
    failed: bool = typer.Option(False, "--failed", help="Run only previously failed tests"),
    clear_cache: bool = typer.Option(False, "--clear-cache", help="Clear the failed tests cache"),
    cache_status: bool = typer.Option(False, "--cache-status", help="Show test failure cache status"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    config: Optional[str] = CONFIG_OPTION,
    environment: Optional[str] = ENVIRONMENT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """Run tests with various modes and options."""
    
    # Handle --failed flag by setting mode
    if failed:
        mode = "failed"
    
    if mode not in ["all", "diff", "package", "failed"]:
        console.print("❌ Invalid mode. Choose from: all, diff, package, failed", style="red")
        raise typer.Exit(1)
    
    try:
        toolkit = get_toolkit(project_root, config, environment)
        
        # Handle cache-related options first
        if clear_cache:
            if 'test_runner' in toolkit.tools:
                runner = toolkit.tools['test_runner'](str(toolkit.config.project_root))
                runner.clear_failure_cache()
                console.print("✅ Test failure cache cleared", style="green")
            else:
                console.print("❌ Test runner not available", style="red")
            return
        
        if cache_status:
            if 'test_runner' in toolkit.tools:
                runner = toolkit.tools['test_runner'](str(toolkit.config.project_root))
                runner.print_cache_status()
            else:
                console.print("❌ Test runner not available", style="red")
            return
        
        kwargs = {}
        if package:
            kwargs['package'] = package
        if workers:
            kwargs['workers'] = workers
        if timeout:
            kwargs['timeout'] = timeout
        if quick:
            kwargs['quick'] = quick
        if enable_coverage:
            kwargs['enable_coverage'] = enable_coverage
            
        if verbose:
            console.print(f"🧪 Running tests in '{mode}' mode...")
            
        results = toolkit.run_tests(mode, **kwargs)
        
        # Display summary table
        if 'summary' in results:
            summary = results['summary']
            
            table = Table(title="Test Results Summary")
            table.add_column("Metric", style="cyan")
            table.add_column("Count", style="green")
            
            table.add_row("Total", str(summary.get('total', 0)))
            table.add_row("Passed", str(summary.get('passed', 0)))
            table.add_row("Failed", str(summary.get('failed', 0)))
            table.add_row("Duration", f"{results.get('execution_time', 0):.2f}s")
            
            # Add special metrics for failed mode
            if mode == "failed":
                if 'cached_failed_count' in results:
                    table.add_row("Cached Failed", str(results['cached_failed_count']))
                if 'now_passing_count' in results:
                    table.add_row("Now Passing", str(results['now_passing_count']))
                if 'still_failing_count' in results:
                    table.add_row("Still Failing", str(results['still_failing_count']))
            
            console.print(table)
            
            # Display mode-specific messages
            if mode == "failed":
                if 'message' in results:
                    console.print(f"ℹ️  {results['message']}", style="yellow")
                elif results.get('now_passing_count', 0) > 0:
                    console.print(f"🎉 {results['now_passing_count']} previously failed tests now pass!", style="green")
            
            # Display detailed test file report
            if 'results' in results and results['results']:
                console.print()
                _display_test_report(results['results'], verbose or show_details)
        else:
            console.print("✅ Tests completed successfully", style="green")
            
    except Exception as e:
        handle_command_error(e, "Test execution", verbose)


@app.command("test-cache")
def test_cache_command(
    action: str = typer.Option("status", help="Cache action: status, clear, history"),
    limit: int = typer.Option(5, help="Number of history entries to show"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    config: Optional[str] = CONFIG_OPTION,
    environment: Optional[str] = ENVIRONMENT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """Manage test failure cache."""
    
    if action not in ["status", "clear", "history"]:
        console.print("❌ Invalid action. Choose from: status, clear, history", style="red")
        raise typer.Exit(1)
    
    try:
        toolkit = get_toolkit(project_root, config, environment)
        
        if 'test_runner' not in toolkit.tools:
            console.print("❌ Test runner not available", style="red")
            raise typer.Exit(1)
        
        runner = toolkit.tools['test_runner'](str(toolkit.config.project_root))
        
        if action == "status":
            runner.print_cache_status()
            
        elif action == "clear":
            runner.clear_failure_cache()
            console.print("✅ Test failure cache cleared", style="green")
            
        elif action == "history":
            history = runner.get_cache_history(limit)
            
            if not history:
                console.print("📜 No test run history available", style="yellow")
                return
            
            console.print(f"📜 Test Run History (last {len(history)} runs):")
            
            for i, entry in enumerate(history):
                timestamp = entry.get('timestamp', 'Unknown')
                summary = entry.get('summary', {})
                failed_count = entry.get('failed_count', 0)
                
                # Format timestamp
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    time_str = timestamp
                
                status_emoji = "✅" if failed_count == 0 else "❌"
                console.print(f"  {i+1}. {status_emoji} {time_str}")
                console.print(f"     Tests: {summary.get('total', 0)} total, "
                            f"{summary.get('passed', 0)} passed, {summary.get('failed', 0)} failed")
                console.print(f"     Duration: {summary.get('execution_time', 0):.2f}s")
                console.print(f"     Mode: {summary.get('mode', 'unknown')}")
                
                if failed_count > 0:
                    failed_tests = entry.get('failed_tests', [])
                    if failed_tests:
                        console.print(f"     Failed tests: {', '.join(failed_tests[:3])}")
                        if len(failed_tests) > 3:
                            console.print(f"     ... and {len(failed_tests) - 3} more")
                console.print()
            
    except Exception as e:
        handle_command_error(e, "Test cache management", verbose)


@app.command("analyze")
def analyze_command(
    analysis_type: str = typer.Option("summary", help="Analysis type: full, summary, circular"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    config: Optional[str] = CONFIG_OPTION,
    environment: Optional[str] = ENVIRONMENT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """Analyze project dependencies."""
    
    if analysis_type not in ["full", "summary", "circular"]:
        console.print("❌ Invalid analysis type. Choose from: full, summary, circular", style="red")
        raise typer.Exit(1)
    
    try:
        toolkit = get_toolkit(project_root, config, environment)
        
        if verbose:
            console.print(f"🔍 Running dependency analysis: {analysis_type}")
            
        results = toolkit.analyze_dependencies(analysis_type)
        
        # Display summary
        if analysis_type == 'circular':
            circular_deps = results.get('circular_dependencies', [])
            if circular_deps:
                console.print("⚠️ Circular dependencies found:", style="yellow")
                for i, dep in enumerate(circular_deps[:5]):
                    console.print(f"  {i+1}. {dep}")
                if len(circular_deps) > 5:
                    console.print(f"  ... and {len(circular_deps) - 5} more")
            else:
                console.print("✅ No circular dependencies found", style="green")
        else:
            console.print("✅ Dependency analysis completed", style="green")
            console.print(f"⏱️ Analysis time: {results.get('execution_time', 0):.2f}s")
            
    except Exception as e:
        handle_command_error(e, "Dependency analysis", verbose)


@app.command("status")
def status_command(
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    config: Optional[str] = CONFIG_OPTION,
    environment: Optional[str] = ENVIRONMENT_OPTION
):
    """Show toolkit status and configuration."""
    
    try:
        toolkit = get_toolkit(project_root, config, environment)
        
        # Basic info panel
        info_text = f"""
📁 Project root: {toolkit.config.project_root}
🌍 Environment: {toolkit.config.environment}
📦 Packages dir: {toolkit.config.packages_dir}
📜 Scripts dir: {toolkit.config.scripts_dir}
📊 Output dir: {toolkit.config.output_dir}
        """
        
        console.print(Panel(info_text.strip(), title="🔧 SAGE Development Toolkit Status", expand=False))
        
        # Tools status
        status_info = toolkit.get_tool_status()
        loaded_tools = status_info['loaded_tools']
        available_tools = status_info['available_tools']
        
        table = Table(title=f"Tools Status ({len(loaded_tools)}/{len(available_tools)} loaded)")
        table.add_column("Tool", style="cyan")
        table.add_column("Status", style="green")
        
        for tool in available_tools:
            status = "✅ Loaded" if tool in loaded_tools else "❌ Not Loaded"
            table.add_row(tool, status)
        
        console.print(table)
        
        # Configuration validation
        errors = toolkit.validate_configuration()
        if errors:
            console.print("⚠️ Configuration Issues:", style="yellow")
            for error in errors:
                console.print(f"  • {error}", style="red")
        else:
            console.print("✅ Configuration is valid", style="green")
            
    except Exception as e:
        handle_command_error(e, "Status check", verbose=False)


@app.command("version")
def version_command():
    """Show version information."""
    console.print("🛠️ SAGE Development Toolkit", style="bold green")
    console.print("Version: 1.0.0")
    console.print("Author: IntelliStream Team")
    console.print("Repository: https://github.com/intellistream/SAGE")


def _display_test_report(test_results, verbose=False):
    """Display detailed test report showing which files passed/failed."""
    from typing import List, Dict
    
    passed_tests = []
    failed_tests = []
    
    # Categorize test results
    for result in test_results:
        test_file = result.get('test_file', 'Unknown')
        log_file = result.get('log_file')  # Extract log file path
        if result.get('passed', False):
            passed_tests.append({
                'file': test_file,
                'duration': result.get('duration', 0),
                'log_file': log_file
            })
        else:
            failed_tests.append({
                'file': test_file,
                'duration': result.get('duration', 0),
                'error': result.get('error', 'Unknown error'),
                'log_file': log_file
            })
    
    # Display passed tests
    if passed_tests:
        console.print("\n✅ Passed Tests:", style="bold green")
        
        if verbose:
            # Show all passed tests with duration
            for test in passed_tests:
                duration_str = f"({test['duration']:.2f}s)" if test['duration'] > 0 else ""
                console.print(f"  ✓ {test['file']} {duration_str}", style="green")
                # Show log file path if available
                log_file = test.get('log_file')
                if log_file:
                    console.print(f"    📄 Log: {log_file}", style="dim cyan")
        else:
            # Show summary for passed tests
            if len(passed_tests) <= 3:
                for test in passed_tests:
                    console.print(f"  ✓ {test['file']}", style="green")
                    # Show log file path if available
                    log_file = test.get('log_file')
                    if log_file:
                        console.print(f"    📄 Log: {log_file}", style="dim cyan")
            else:
                # Show first 2 and indicate more
                for test in passed_tests[:2]:
                    console.print(f"  ✓ {test['file']}", style="green")
                    # Show log file path if available
                    log_file = test.get('log_file')
                    if log_file:
                        console.print(f"    📄 Log: {log_file}", style="dim cyan")
                console.print(f"  ✓ ... and {len(passed_tests) - 2} more passed tests", style="dim green")
    
    # Display failed tests
    if failed_tests:
        console.print("\n❌ Failed Tests:", style="bold red")
        
        for test in failed_tests:
            duration_str = f"({test['duration']:.2f}s)" if test['duration'] > 0 else ""
            console.print(f"  ✗ {test['file']} {duration_str}", style="red")
            
            # Show log file path if available
            log_file = test.get('log_file')
            if log_file:
                console.print(f"    📄 Log: {log_file}", style="dim cyan")
            
            if verbose and test['error']:
                # Show error details in verbose mode
                error_lines = test['error'].split('\n')[:3]  # First 3 lines
                for line in error_lines:
                    if line.strip():
                        console.print(f"    {line.strip()}", style="dim red")
                if len(test['error'].split('\n')) > 3:
                    console.print("    ...", style="dim red")
    
    # Overall status
    console.print()
    if not failed_tests:
        console.print("🎉 All tests passed!", style="bold green")
    else:
        total_tests = len(passed_tests) + len(failed_tests)
        console.print(f"📊 Test Status: {len(passed_tests)}/{total_tests} passed, {len(failed_tests)} failed", 
                     style="yellow" if failed_tests else "green")
