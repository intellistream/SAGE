"""
Test command implementation.
"""

import typer
from ..core import BaseCommand, console, handle_command_error


class TestCommand(BaseCommand):
    """测试命令"""
    
    def __init__(self):
        super().__init__("test", "Run tests with various modes and options")
    
    def _register_commands(self):
        """注册测试相关命令"""
        
        @self.app.command("run")
        def test_run(
            mode: str = typer.Option("all", help="Test mode: all, changed, diff, failed"),
            pattern: str = typer.Option("test_*.py", help="Test file pattern"),
            verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
            project_root: str = typer.Option(None, help="Project root directory")
        ):
            """Run tests with various modes"""
            def _run_tests(toolkit, **kwargs):
                return toolkit.run_tests(
                    mode=mode,
                    pattern=pattern,
                    verbose=verbose,
                    **kwargs
                )
            
            self.execute_with_toolkit(_run_tests, 
                                    project_root=project_root, 
                                    verbose=verbose)
        
        @self.app.command("cache")
        def test_cache(
            action: str = typer.Argument(help="Cache action: clear, list, status"),
            verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
            project_root: str = typer.Option(None, help="Project root directory")
        ):
            """Manage test failure cache"""
            def _manage_cache(toolkit, **kwargs):
                return toolkit.manage_test_cache(action=action, **kwargs)
            
            self.execute_with_toolkit(_manage_cache,
                                    project_root=project_root,
                                    verbose=verbose)
        
        @self.app.command("list")
        def list_tests(
            verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
            project_root: str = typer.Option(None, help="Project root directory")
        ):
            """List all available tests"""
            def _list_tests(toolkit, **kwargs):
                return toolkit.list_tests(**kwargs)
            
            self.execute_with_toolkit(_list_tests,
                                    project_root=project_root,
                                    verbose=verbose)


# 创建命令实例
command = TestCommand()
app = command.app
