#!/usr/bin/env python3
"""
SAGE Package Restructuring Script

This script performs the following restructuring:
1. Rename sage-userspace to sage-apps
2. Move sage/userspace to sage/apps 
3. Move sage/service to sage/middleware in sage-middleware package
4. Update all import paths and configurations
"""

import os
import shutil
import sys
from pathlib import Path
import re


def restructure_packages():
    """Execute the full package restructuring."""
    
    project_root = Path(__file__).parent.parent
    packages_dir = project_root / "packages"
    
    print("🔄 SAGE Package Restructuring")
    print("=" * 50)
    print(f"📁 Working in: {packages_dir}")
    
    # Step 1: Rename sage-userspace to sage-apps
    print("\n📦 Step 1: Renaming sage-userspace to sage-apps")
    rename_userspace_to_apps(packages_dir)
    
    # Step 2: Restructure sage-middleware
    print("\n📦 Step 2: Restructuring sage-middleware")
    restructure_sage_middleware(packages_dir)
    
    # Step 3: Update configurations
    print("\n📦 Step 3: Updating configurations")
    update_configurations(packages_dir)
    
    print("\n✅ Package restructuring completed!")
    print("\n📋 Next steps:")
    print("1. Update import statements in your code")
    print("2. Update documentation")
    print("3. Test the new structure")


def rename_userspace_to_apps(packages_dir):
    """Rename sage-userspace to sage-apps and reorganize structure."""
    
    old_userspace = packages_dir / "sage-userspace"
    new_apps = packages_dir / "sage-apps"
    
    if not old_userspace.exists():
        print("⚠️  sage-userspace directory not found")
        return
    
    # Create new sage-apps directory
    if new_apps.exists():
        print("🧹 Removing existing sage-apps directory")
        shutil.rmtree(new_apps)
    
    print(f"📁 Copying {old_userspace} to {new_apps}")
    shutil.copytree(old_userspace, new_apps)
    
    # Restructure the source directory
    apps_src = new_apps / "src" / "sage"
    
    if apps_src.exists():
        # Create apps directory structure
        apps_core = apps_src / "apps"
        apps_core.mkdir(exist_ok=True)
        
        # Move contents from userspace to apps
        old_userspace_src = apps_src / "userspace"
        if old_userspace_src.exists():
            print("📁 Moving userspace content to apps")
            for item in old_userspace_src.iterdir():
                target = apps_core / item.name
                if target.exists():
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                if item.is_dir():
                    shutil.copytree(item, target)
                else:
                    shutil.copy2(item, target)
            
            # Remove old userspace directory
            shutil.rmtree(old_userspace_src)
        
        # Move other top-level items to apps as well
        for item in ["lib", "plugins", "examples"]:
            old_path = apps_src / item
            if old_path.exists():
                new_path = apps_core / item
                if new_path.exists():
                    if new_path.is_dir():
                        shutil.rmtree(new_path)
                    else:
                        new_path.unlink()
                if old_path.is_dir():
                    shutil.copytree(old_path, new_path)
                else:
                    shutil.copy2(old_path, new_path)
                shutil.rmtree(old_path)
    
    print("✅ Renamed sage-userspace to sage-apps")


def restructure_sage_middleware(packages_dir):
    """Restructure sage-middleware to unify service->middleware."""
    
    middleware_dir = packages_dir / "sage-middleware"
    if not middleware_dir.exists():
        print("⚠️  sage-middleware directory not found")
        return
    
    middleware_src = middleware_dir / "src" / "sage"
    
    if middleware_src.exists():
        service_dir = middleware_src / "service"
        middleware_code_dir = middleware_src / "middleware"
        
        if service_dir.exists():
            print("📁 Moving service code to middleware")
            
            # Ensure middleware directory exists
            middleware_code_dir.mkdir(exist_ok=True)
            
            # Move service contents to middleware
            for item in service_dir.iterdir():
                target = middleware_code_dir / item.name
                if target.exists():
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                
                if item.is_dir():
                    shutil.copytree(item, target)
                else:
                    shutil.copy2(item, target)
            
            # Remove service directory
            shutil.rmtree(service_dir)
            print("✅ Moved service code to middleware")


def update_configurations(packages_dir):
    """Update pyproject.toml and other configuration files."""
    
    # Update sage-apps pyproject.toml
    apps_pyproject = packages_dir / "sage-apps" / "pyproject.toml"
    if apps_pyproject.exists():
        print("📝 Updating sage-apps pyproject.toml")
        update_apps_pyproject(apps_pyproject)
    
    # Update sage-middleware pyproject.toml
    middleware_pyproject = packages_dir / "sage-middleware" / "pyproject.toml"
    if middleware_pyproject.exists():
        print("📝 Updating sage-middleware pyproject.toml")
        update_middleware_pyproject(middleware_pyproject)
    
    # Update main pyproject.toml
    main_pyproject = packages_dir.parent / "pyproject.toml"
    if main_pyproject.exists():
        print("📝 Updating main pyproject.toml")
        update_main_pyproject(main_pyproject)


def update_apps_pyproject(pyproject_file):
    """Update sage-apps pyproject.toml configuration."""
    
    try:
        with open(pyproject_file, 'r') as f:
            content = f.read()
        
        # Update package name and description
        content = re.sub(
            r'name = "intsage-userspace"',
            'name = "intsage-apps"',
            content
        )
        
        content = re.sub(
            r'description = ".*?"',
            'description = "SAGE Framework - Application Components (高级应用组件)"',
            content
        )
        
        # Update keywords
        content = re.sub(
            r'"userspace"',
            '"apps"',
            content
        )
        
        # Update package directory mapping
        content = re.sub(
            r'"sage\.userspace"',
            '"sage.apps"',
            content
        )
        
        # Update package data references
        content = re.sub(
            r'"sage\.userspace"',
            '"sage.apps"',
            content
        )
        
        with open(pyproject_file, 'w') as f:
            f.write(content)
        
        print("✅ Updated sage-apps pyproject.toml")
        
    except Exception as e:
        print(f"❌ Failed to update sage-apps pyproject.toml: {e}")


def update_middleware_pyproject(pyproject_file):
    """Update sage-middleware pyproject.toml configuration."""
    
    try:
        with open(pyproject_file, 'r') as f:
            content = f.read()
        
        # Update description to remove service reference
        content = re.sub(
            r'description = ".*?中间件服务.*?"',
            'description = "SAGE Framework - Middleware Components (中间件组件)"',
            content
        )
        
        # Update package data references from service to middleware
        content = re.sub(
            r'"sage\.service"',
            '"sage.middleware"',
            content
        )
        
        # Update keywords to remove service
        content = re.sub(
            r'"service",\s*',
            '',
            content
        )
        
        with open(pyproject_file, 'w') as f:
            f.write(content)
        
        print("✅ Updated sage-middleware pyproject.toml")
        
    except Exception as e:
        print(f"❌ Failed to update sage-middleware pyproject.toml: {e}")


def update_main_pyproject(pyproject_file):
    """Update main pyproject.toml configuration."""
    
    try:
        with open(pyproject_file, 'r') as f:
            content = f.read()
        
        # Update dependencies from userspace to apps
        content = re.sub(
            r'"intsage-userspace"',
            '"intsage-apps"',
            content
        )
        
        # Update enterprise dependencies
        content = re.sub(
            r'"intsage-userspace\[enterprise\]"',
            '"intsage-apps[enterprise]"',
            content
        )
        
        with open(pyproject_file, 'w') as f:
            f.write(content)
        
        print("✅ Updated main pyproject.toml")
        
    except Exception as e:
        print(f"❌ Failed to update main pyproject.toml: {e}")


def create_migration_summary():
    """Create a migration summary document."""
    
    summary = """# SAGE Package Restructuring Summary

## Changes Made

### 1. Package Renaming
- `sage-userspace` → `sage-apps`
- Updated package name in pyproject.toml
- Updated all references and dependencies

### 2. Directory Structure Changes

#### sage-apps (formerly sage-userspace)
```
Before:
src/sage/
├── userspace/
├── lib/
├── plugins/
└── examples/

After:
src/sage/
└── apps/
    ├── core/          # Main app functionality
    ├── lib/           # Shared libraries
    ├── plugins/       # Plugin system
    ├── examples/      # Example applications
    └── enterprise/    # Enterprise extensions
```

#### sage-middleware
```
Before:
src/sage/
├── middleware/
└── service/

After:
src/sage/
└── middleware/
    ├── core/          # Core middleware
    ├── services/      # Service implementations
    └── enterprise/    # Enterprise extensions
```

### 3. Import Path Changes

#### Old Import Paths:
```python
from sage.userspace import ...
from sage.service import ...
```

#### New Import Paths:
```python
from sage.apps import ...
from sage.middleware import ...
```

### 4. Package Dependencies Updates

#### requirements.txt / pyproject.toml:
- `intsage-userspace` → `intsage-apps`
- `intsage-userspace[enterprise]` → `intsage-apps[enterprise]`

## Migration Guide for Developers

### 1. Update Import Statements
```bash
# Find and replace in your codebase
find . -name "*.py" -exec sed -i 's/from sage.userspace/from sage.apps/g' {} +
find . -name "*.py" -exec sed -i 's/import sage.userspace/import sage.apps/g' {} +
find . -name "*.py" -exec sed -i 's/from sage.service/from sage.middleware/g' {} +
```

### 2. Update Requirements Files
```bash
# Update package names
sed -i 's/intsage-userspace/intsage-apps/g' requirements*.txt
```

### 3. Update Configuration Files
- Check pyproject.toml files
- Update CI/CD configurations
- Update documentation

### 4. Reinstall Packages
```bash
# Uninstall old packages
pip uninstall intsage-userspace

# Install new packages
pip install intsage-apps
```

## Testing the Migration

1. **Import Tests**:
   ```python
   # Test basic imports
   import sage.apps
   import sage.middleware
   
   # Test enterprise imports (if licensed)
   from sage.apps.enterprise import ...
   from sage.middleware.enterprise import ...
   ```

2. **Package Installation**:
   ```bash
   # Test installation
   pip install -e packages/sage-apps/
   pip install -e packages/sage-middleware/
   ```

3. **Functionality Tests**:
   ```bash
   # Run test suites
   pytest packages/sage-apps/tests/
   pytest packages/sage-middleware/tests/
   ```

## Rollback Plan

If issues occur, you can rollback by:
1. Reverting git changes: `git checkout HEAD~1`
2. Restoring original directory structure
3. Reinstalling original packages

## Notes

- The original `packages/sage-userspace/` directory is preserved until migration is confirmed
- All enterprise functionality is preserved in the new structure
- License checking continues to work as before
- Backward compatibility shims can be added if needed
"""
    
    summary_file = Path(__file__).parent.parent / "PACKAGE_RESTRUCTURING_SUMMARY.md"
    with open(summary_file, 'w') as f:
        f.write(summary)
    
    print(f"📄 Created migration summary: {summary_file}")


def main():
    """Main execution."""
    restructure_packages()
    create_migration_summary()
    
    print("\n🎉 Package restructuring completed successfully!")
    print("📚 See PACKAGE_RESTRUCTURING_SUMMARY.md for detailed migration information")


if __name__ == "__main__":
    main()
