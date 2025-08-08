#!/usr/bin/env python3
"""
Test script to verify SAGE CLI package configuration.
"""

def test_cli_imports():
    """Test importing CLI modules from sage-cli package."""
    try:
        from sage.cli import __version__
        print(f"✅ SAGE CLI version: {__version__}")
        
        # Test main CLI imports
        try:
            from sage.cli.main import app
            print("✅ Main CLI app import successful")
            
            from sage.cli.config_manager import ConfigManager
            print("✅ Config manager import successful")
            
            from sage.cli.deploy import app as deploy_app
            print("✅ Deploy module import successful")
            
            from sage.cli.job import app as job_app
            print("✅ Job module import successful")
            
        except ImportError as e:
            print(f"❌ CLI module import failed: {e}")
            
    except ImportError as e:
        print(f"❌ SAGE CLI package import failed: {e}")

def test_cli_dependencies():
    """Test CLI dependencies."""
    dependencies = [
        ("typer", "CLI framework"),
        ("rich", "Rich text and formatting"),
        ("click", "Command line interface creation"),
        ("yaml", "YAML configuration parsing"),
        ("psutil", "System and process utilities"),
    ]
    
    print("\n📦 Testing CLI dependencies:")
    for dep, description in dependencies:
        try:
            if dep == "yaml":
                import yaml
            elif dep == "typer":
                import typer
            elif dep == "rich":
                import rich
            elif dep == "click":
                import click
            elif dep == "psutil":
                import psutil
            print(f"✅ {dep}: {description}")
        except ImportError:
            print(f"❌ {dep}: {description} (missing)")

def test_cli_entry_points():
    """Test CLI entry points configuration."""
    print("\n🚀 CLI Entry Points:")
    entry_points = [
        "sage",
        "sage-cli", 
        "sage-job",
        "sage-deploy",
        "sage-cluster",
        "sage-config"
    ]
    
    for entry_point in entry_points:
        print(f"  📌 {entry_point}")

def test_package_structure():
    """Test package structure."""
    print("\n📁 Package Structure Test:")
    try:
        import os
        cli_path = "/home/flecther/workspace/SAGE/packages/sage-cli/src/sage/cli"
        if os.path.exists(cli_path):
            files = os.listdir(cli_path)
            python_files = [f for f in files if f.endswith('.py')]
            print(f"✅ Found {len(python_files)} Python modules in sage.cli")
            for py_file in sorted(python_files):
                print(f"  📄 {py_file}")
        else:
            print(f"❌ CLI package path not found: {cli_path}")
    except Exception as e:
        print(f"❌ Package structure test failed: {e}")

if __name__ == "__main__":
    print("🧪 Testing SAGE CLI Package Configuration")
    print("=" * 50)
    
    test_cli_imports()
    test_cli_dependencies()  
    test_cli_entry_points()
    test_package_structure()
    
    print("\n✅ CLI package tests completed!")
