"""
Compile command implementation.
"""

import typer
from typing import Optional
from pathlib import Path
from .common import console, get_toolkit, handle_command_error, VERBOSE_OPTION, PROJECT_ROOT_OPTION


app = typer.Typer(name="compile", help="🔧 Compile Python packages to bytecode")


@app.command()
def package(
    package_path: Optional[str] = typer.Argument(None, help="Path to package to compile"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory"),
    build_wheel: bool = typer.Option(False, "--build", "-b", help="Build wheel after compilation"),
    upload: bool = typer.Option(False, "--upload", "-u", help="Upload to PyPI after building"),
    dry_run: bool = typer.Option(True, "--dry-run", help="Dry run mode"),
    use_sage_home: bool = typer.Option(True, "--use-sage-home", help="Use ~/.sage/dist as output"),
    create_symlink: bool = typer.Option(True, "--create-symlink", help="Create .sage symlink"),
    project_root: str = PROJECT_ROOT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """🔧 Compile Python packages to bytecode (.pyc files) to hide source code"""
    try:
        toolkit = get_toolkit(project_root=project_root)
        
        if verbose:
            console.print(f"🔧 Compiling package: {package_path or 'all packages'}", style="blue")
        
        result = toolkit.compile_package(
            package_path=package_path,
            output_dir=output_dir,
            build_wheel=build_wheel,
            upload=upload,
            dry_run=dry_run,
            use_sage_home=use_sage_home,
            create_symlink=create_symlink,
            verbose=verbose
        )
        
        if dry_run:
            console.print("🎭 Compilation preview completed", style="yellow")
            console.print("💡 Use --no-dry-run to perform actual compilation", style="blue")
        else:
            console.print("✅ Package compilation completed", style="green")
            
        if result.get('compiled_path'):
            console.print(f"📦 Output: {result['compiled_path']}", style="blue")
        
    except Exception as e:
        handle_command_error(e, "Compilation", verbose)


@app.command()
def info():
    """Show SAGE home directory information"""
    try:
        from ...core.bytecode_compiler import _get_sage_home_info
        _get_sage_home_info()
        
    except Exception as e:
        console.print(f"❌ Failed to get SAGE home info: {e}", style="red")
        raise typer.Exit(1)
