#!/usr/bin/env python3
"""
Simple SAGE Installation Script

A lightweight alternative to complex shell scripts for managing SAGE installations.
This script integrates with the existing pip-based workflow.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional


def print_colored(message: str, color: str = "blue"):
    """Print colored message."""
    colors = {
        "red": "\033[0;31m",
        "green": "\033[0;32m", 
        "yellow": "\033[1;33m",
        "blue": "\033[0;34m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}{message}{colors['reset']}")


def find_project_root() -> Path:
    """Find SAGE project root."""
    current = Path(__file__).parent.parent
    if (current / "packages").exists() and (current / "pyproject.toml").exists():
        return current
    return Path.cwd()


def check_license_simple() -> Dict[str, any]:
    """Simple license check without complex imports."""
    # Check environment variable first
    license_key = os.environ.get("SAGE_LICENSE_KEY")
    if license_key and license_key.startswith("SAGE-"):
        return {
            "has_license": True,
            "source": "environment",
            "type": "commercial",
            "key": license_key[:20] + "..."
        }
    
    # Check license file
    license_file = Path.home() / ".sage" / "license.key"
    if license_file.exists():
        try:
            with open(license_file, 'r') as f:
                file_key = f.read().strip()
            if file_key.startswith("SAGE-"):
                return {
                    "has_license": True,
                    "source": "file", 
                    "type": "commercial",
                    "key": file_key[:20] + "..."
                }
        except:
            pass
    
    return {
        "has_license": False,
        "source": "none",
        "type": "open-source"
    }


def install_requirements(requirements_file: str, project_root: Path) -> bool:
    """Install from requirements file."""
    req_file = project_root / requirements_file
    if not req_file.exists():
        print_colored(f"❌ Requirements file not found: {req_file}", "red")
        return False
    
    print_colored(f"📦 Installing from {requirements_file}...", "blue")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(req_file)
        ], check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print_colored(f"❌ Installation failed: {e.stderr}", "red")
        return False


def main():
    """Main installation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple SAGE Installation")
    parser.add_argument("--edition", choices=["core", "dev", "enterprise"], 
                       default="core", help="Edition to install")
    parser.add_argument("--license-key", help="License key for enterprise features")
    parser.add_argument("--check", action="store_true", help="Check installation status")
    parser.add_argument("--force", action="store_true", help="Force installation")
    
    args = parser.parse_args()
    
    project_root = find_project_root()
    print_colored(f"🏗️  SAGE Simple Installer", "blue")
    print_colored(f"📁 Project root: {project_root}", "blue")
    
    # Set license key if provided
    if args.license_key:
        os.environ["SAGE_LICENSE_KEY"] = args.license_key
        print_colored(f"🔑 Using license key: {args.license_key[:20]}...", "green")
    
    # Check status
    if args.check:
        license_status = check_license_simple()
        print_colored("\n🔍 Installation Status:", "blue")
        print_colored(f"License: {license_status['type']}", "green" if license_status['has_license'] else "yellow")
        print_colored(f"Source: {license_status['source']}", "blue")
        
        if license_status['has_license']:
            print_colored(f"Key: {license_status['key']}", "green")
        
        return 0
    
    # Install based on edition
    if args.edition == "core":
        print_colored("\n📦 Installing SAGE Core Edition", "blue")
        success = install_requirements("requirements.txt", project_root)
        
    elif args.edition == "dev":
        print_colored("\n📦 Installing SAGE Development Edition", "blue")
        success = (
            install_requirements("requirements.txt", project_root) and
            install_requirements("requirements-dev.txt", project_root)
        )
        
    elif args.edition == "enterprise":
        print_colored("\n📦 Installing SAGE Enterprise Edition", "blue")
        
        # Check license for enterprise
        license_status = check_license_simple()
        if not license_status['has_license'] and not args.force:
            print_colored("❌ Enterprise edition requires a valid license", "red")
            print_colored("💡 Get a license and use: --license-key YOUR-KEY", "yellow")
            print_colored("💡 Or use --force to install anyway", "yellow")
            return 1
        
        if license_status['has_license']:
            print_colored(f"✅ Valid license found: {license_status['key']}", "green")
        elif args.force:
            print_colored("⚠️  Installing without license verification", "yellow")
        
        success = install_requirements("requirements-commercial.txt", project_root)
    
    else:
        print_colored(f"❌ Unknown edition: {args.edition}", "red")
        return 1
    
    # Summary
    if success:
        print_colored(f"\n🎉 SAGE {args.edition} edition installed successfully!", "green")
        print_colored("💡 You can now import and use SAGE in your Python code", "blue")
        
        if args.edition == "enterprise":
            print_colored("🏢 Enterprise features are now available", "green")
            
    else:
        print_colored(f"\n💥 Installation failed", "red")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
