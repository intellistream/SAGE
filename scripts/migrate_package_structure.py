#!/usr/bin/env python3
"""
Package Structure Migration Script

This script migrates the current packages/commercial/ structure to a proper
optional dependencies structure where commercial features are integrated
into their corresponding open source packages.
"""

import os
import shutil
from pathlib import Path
import json


def migrate_package_structure():
    """Migrate commercial packages into main packages as optional features."""
    
    project_root = Path(__file__).parent.parent
    packages_dir = project_root / "packages"
    commercial_dir = packages_dir / "commercial"
    
    print("🔄 Migrating package structure...")
    print(f"Project root: {project_root}")
    print(f"Commercial dir: {commercial_dir}")
    
    if not commercial_dir.exists():
        print("❌ Commercial directory not found")
        return
    
    migrations = [
        {
            "name": "sage-kernel",
            "commercial_src": commercial_dir / "sage-kernel" / "src" / "sage" / "kernel",
            "target_pkg": packages_dir / "sage-kernel" / "src" / "sage" / "kernel",
            "commercial_components": ["sage_queue", "enterprise"]
        },
        {
            "name": "sage-middleware", 
            "commercial_src": commercial_dir / "sage-middleware" / "src" / "sage" / "middleware",
            "target_pkg": packages_dir / "sage-middleware" / "src" / "sage" / "middleware",
            "commercial_components": ["sage_db"]
        },
        {
            "name": "sage-userspace",
            "commercial_src": commercial_dir / "sage-userspace" / "src" / "sage" / "userspace", 
            "target_pkg": packages_dir / "sage-userspace" / "src" / "sage" / "userspace",
            "commercial_components": ["runtime", "analytics"]
        }
    ]
    
    for migration in migrations:
        migrate_single_package(migration)
    
    print("✅ Migration completed")


def migrate_single_package(migration_config):
    """Migrate a single package's commercial features."""
    
    name = migration_config["name"]
    commercial_src = migration_config["commercial_src"]
    target_pkg = migration_config["target_pkg"]
    components = migration_config["commercial_components"]
    
    print(f"\n📦 Migrating {name}...")
    
    # Check if commercial source exists
    if not commercial_src.exists():
        print(f"⚠️  Commercial source not found: {commercial_src}")
        return
    
    # Create commercial directory in target package
    commercial_target = target_pkg / "commercial"
    commercial_target.mkdir(exist_ok=True)
    
    # Create __init__.py with license check
    init_content = f'''"""
{name} Commercial Extensions

This module contains commercial features that require a valid SAGE license.
"""

import os
import sys
from pathlib import Path

# License validation
def _check_commercial_license():
    """Check if commercial features are licensed."""
    try:
        # Try to import license validator
        project_root = Path(__file__).parent.parent.parent.parent.parent
        license_tools = project_root / "tools" / "license"
        
        if license_tools.exists():
            sys.path.insert(0, str(license_tools))
            sys.path.insert(0, str(license_tools / "shared"))
            
            from shared.validation import LicenseValidator
            validator = LicenseValidator()
            
            if not validator.has_valid_license():
                return False
                
            features = validator.get_license_features()
            # Check for relevant commercial features
            commercial_features = ["enterprise", "high-performance", "enterprise-db", "advanced-analytics"]
            return any(feature in features for feature in commercial_features)
            
    except ImportError:
        pass
    except Exception:
        pass
    
    # Fallback: check environment variable
    return os.getenv("SAGE_COMMERCIAL_ENABLED", "").lower() in ("true", "1", "yes")


# Only expose commercial features if licensed
if _check_commercial_license():
    # Import commercial components
    try:
{chr(10).join(f"        from .{component} import *" for component in components)}
    except ImportError as e:
        print(f"Warning: Could not import commercial component: {{e}}")
else:
    print(f"ℹ️  Commercial features for {name} not available - license required")
    # Could expose limited functionality or placeholders here

__all__ = {components}
'''
    
    with open(commercial_target / "__init__.py", "w") as f:
        f.write(init_content)
    
    # Copy commercial components
    for component in components:
        src_component = commercial_src / component
        target_component = commercial_target / component
        
        if src_component.exists():
            print(f"  📁 Copying {component}...")
            if src_component.is_dir():
                shutil.copytree(src_component, target_component, dirs_exist_ok=True)
            else:
                shutil.copy2(src_component, target_component)
        else:
            print(f"  ⚠️  Component not found: {src_component}")
    
    print(f"✅ {name} migration completed")


if __name__ == "__main__":
    migrate_package_structure()
