#!/usr/bin/env python3
"""
Commercial Code Migration Script

This script properly migrates commercial code from packages/commercial/
to the corresponding open source packages as enterprise extensions.
"""

import os
import shutil
import sys
from pathlib import Path


def migrate_commercial_code():
    """Migrate commercial code to enterprise extensions."""
    
    project_root = Path(__file__).parent.parent
    commercial_dir = project_root / "packages" / "commercial"
    packages_dir = project_root / "packages"
    
    print("🔄 Migrating commercial code to enterprise extensions...")
    print(f"📁 Commercial source: {commercial_dir}")
    print(f"📁 Target packages: {packages_dir}")
    
    if not commercial_dir.exists():
        print("❌ Commercial directory not found!")
        return False
    
    migration_map = {
        "sage-kernel": {
            "source": commercial_dir / "sage-kernel" / "src" / "sage" / "kernel",
            "target": packages_dir / "sage-kernel" / "src" / "sage" / "kernel" / "enterprise",
            "components": ["sage_queue"]
        },
        "sage-middleware": {
            "source": commercial_dir / "sage-middleware" / "src" / "sage" / "middleware", 
            "target": packages_dir / "sage-middleware" / "src" / "sage" / "middleware" / "enterprise",
            "components": ["sage_db"]
        },
        "sage-userspace": {
            "source": commercial_dir / "sage-userspace" / "src" / "sage" / "userspace",
            "target": packages_dir / "sage-userspace" / "src" / "sage" / "userspace" / "enterprise", 
            "components": []
        }
    }
    
    for package_name, config in migration_map.items():
        print(f"\n📦 Migrating {package_name}...")
        
        source_dir = config["source"]
        target_dir = config["target"]
        
        if not source_dir.exists():
            print(f"⚠️  Source not found: {source_dir}")
            continue
        
        # Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean up duplicate enterprise directory if exists
        duplicate_enterprise = target_dir / "enterprise"
        if duplicate_enterprise.exists():
            print(f"🧹 Cleaning up duplicate enterprise directory...")
            shutil.rmtree(duplicate_enterprise)
        
        # Migrate components
        migrated_count = 0
        for item in source_dir.iterdir():
            if item.name in ["__init__.py", "enterprise"]:
                continue
                
            target_item = target_dir / item.name
            
            if item.is_dir():
                if target_item.exists():
                    shutil.rmtree(target_item)
                shutil.copytree(item, target_item)
                print(f"  📁 Migrated directory: {item.name}")
            else:
                shutil.copy2(item, target_item)
                print(f"  📄 Migrated file: {item.name}")
            
            migrated_count += 1
        
        # Create __init__.py for enterprise module
        enterprise_init = target_dir / "__init__.py"
        if not enterprise_init.exists():
            with open(enterprise_init, 'w') as f:
                f.write(f'''"""
SAGE {package_name.title()} Enterprise Extensions

This module provides enterprise-grade extensions for SAGE {package_name}.
Requires a valid commercial license.
"""

import os
import sys
from pathlib import Path

# License validation
def _check_enterprise_license():
    """Check if enterprise features are licensed."""
    try:
        # Try to find license tools
        current_dir = Path(__file__).parent
        project_root = current_dir
        for _ in range(10):  # Search up to 10 levels
            if (project_root / "tools" / "license").exists():
                break
            project_root = project_root.parent
        else:
            return False
        
        # Add license tools to path
        license_tools = project_root / "tools" / "license"
        sys.path.insert(0, str(license_tools))
        sys.path.insert(0, str(license_tools / "shared"))
        
        from shared.validation import LicenseValidator
        
        validator = LicenseValidator()
        if not validator.has_valid_license():
            return False
        
        features = validator.get_license_features()
        enterprise_features = ["high-performance", "enterprise-db", "advanced-analytics", "enterprise"]
        
        return any(f in features for f in enterprise_features)
        
    except ImportError:
        # License system not available - allow in development
        return True
    except Exception:
        return False

# Check license on import
_ENTERPRISE_LICENSED = _check_enterprise_license()

def require_license(func):
    """Decorator to require enterprise license for function access."""
    def wrapper(*args, **kwargs):
        if not _ENTERPRISE_LICENSED:
            raise ImportError(
                f"Enterprise feature '{{func.__name__}}' requires a valid SAGE commercial license. "
                f"Contact sales@sage.ai for licensing information."
            )
        return func(*args, **kwargs)
    return wrapper

# Export license check function
__all__ = ['require_license', '_ENTERPRISE_LICENSED']
''')
        
        print(f"✅ Migrated {migrated_count} items for {package_name}")
    
    print(f"\n🎉 Commercial code migration completed!")
    print("\n📋 Next steps:")
    print("1. Update pyproject.toml files with [enterprise] optional dependencies")
    print("2. Test enterprise imports with license validation")
    print("3. Remove packages/commercial/ directory when satisfied")
    
    return True


def update_package_configs():
    """Update pyproject.toml files with enterprise configurations."""
    
    project_root = Path(__file__).parent.parent
    packages_dir = project_root / "packages"
    
    configs = {
        "sage-kernel": {
            "enterprise_deps": [
                "numpy>=1.21.0",
                "scipy>=1.7.0", 
                "cython>=0.29.0",
            ],
            "description": "High-performance kernel infrastructure and queue management"
        },
        "sage-middleware": {
            "enterprise_deps": [
                "sqlalchemy>=1.4.0",
                "psycopg2-binary>=2.9.0",
                "redis>=4.0.0",
            ],
            "description": "Enterprise database and storage middleware"
        },
        "sage-userspace": {
            "enterprise_deps": [
                "pandas>=1.3.0",
                "scikit-learn>=1.0.0",
                "matplotlib>=3.5.0",
            ],
            "description": "Advanced analytics and visualization components"
        }
    }
    
    for package_name, config in configs.items():
        package_dir = packages_dir / package_name
        pyproject_file = package_dir / "pyproject.toml"
        
        if not pyproject_file.exists():
            print(f"⚠️  pyproject.toml not found for {package_name}")
            continue
        
        print(f"📝 Updating {package_name} configuration...")
        
        # This would require toml parsing - for now just show what needs to be added
        print(f"  📄 Add enterprise dependencies: {config['enterprise_deps']}")
        print(f"  📄 Description: {config['description']}")


def main():
    """Main execution."""
    print("🚀 SAGE Commercial Code Migration")
    print("=" * 50)
    
    if not migrate_commercial_code():
        print("❌ Migration failed!")
        return 1
    
    print("\n" + "=" * 50)
    update_package_configs()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
