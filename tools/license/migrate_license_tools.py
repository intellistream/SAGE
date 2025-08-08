#!/usr/bin/env python3
"""
SAGE License Migration Tool
Migrate from legacy scripts/sage-license.py to new tools/license/ structure
"""

import os
import shutil
import sys
from pathlib import Path


def migrate_license_tools():
    """Migrate license management to new structure"""
    print("🔄 SAGE License Tools Migration")
    print("=" * 40)
    
    project_root = Path(__file__).parent.parent
    old_script = project_root / "scripts" / "sage-license.py"
    new_tools_dir = project_root / "tools" / "license"
    
    # Check if old script exists
    if not old_script.exists():
        print("✅ No legacy sage-license.py found - already migrated")
        return True
    
    print(f"📁 Found legacy script: {old_script}")
    print(f"🎯 Target directory: {new_tools_dir}")
    
    # Check if new tools exist
    if new_tools_dir.exists():
        print("✅ New license tools already exist")
        
        # Create backup of old script
        backup_path = old_script.with_suffix('.py.backup')
        if not backup_path.exists():
            shutil.copy2(old_script, backup_path)
            print(f"💾 Created backup: {backup_path}")
        
        # Create deprecation notice
        deprecation_script = project_root / "scripts" / "sage-license.py"
        with open(deprecation_script, 'w') as f:
            f.write(f'''#!/usr/bin/env python3
"""
DEPRECATED: SAGE License Management

This script has been moved to tools/license/ for better organization.
Please use the new license management tools:

  python tools/license/sage_license.py <command>

Commands:
  install <key>     - Install license
  status           - Check status
  remove           - Remove license
  generate <name>  - Generate license (vendor)
  list             - List licenses (vendor)
"""

import sys
import subprocess
from pathlib import Path

def main():
    print("🚨 DEPRECATED SCRIPT")
    print("This script has been moved to tools/license/")
    print("")
    print("Please use instead:")
    print("  python tools/license/sage_license.py", " ".join(sys.argv[1:]))
    print("")
    
    # Forward to new script
    new_script = Path(__file__).parent.parent / "tools" / "license" / "sage_license.py"
    if new_script.exists():
        cmd = [sys.executable, str(new_script)] + sys.argv[1:]
        subprocess.run(cmd)
    else:
        print("❌ New license tools not found!")
        sys.exit(1)

if __name__ == '__main__':
    main()
''')
        
        print("✅ Updated scripts/sage-license.py with deprecation notice")
        
    else:
        print("❌ New license tools not found!")
        return False
    
    # Update documentation references
    docs_updated = update_documentation_references(project_root)
    if docs_updated:
        print("✅ Updated documentation references")
    
    print("")
    print("🎉 Migration completed successfully!")
    print("")
    print("Next steps:")
    print("1. Test new license tools: python tools/license/sage_license.py status")
    print("2. Update your scripts to use new paths")
    print("3. Remove backup files when confident in migration")
    
    return True


def update_documentation_references(project_root):
    """Update documentation to reference new license tools"""
    updates_made = False
    
    # Files to update
    doc_files = [
        project_root / "README.md",
        project_root / "INSTALL_GUIDE.md",
        project_root / "docs" / "LICENSE_MANAGEMENT.md"
    ]
    
    for doc_file in doc_files:
        if not doc_file.exists():
            continue
            
        try:
            with open(doc_file, 'r') as f:
                content = f.read()
            
            # Check if updates are needed
            if 'scripts/sage-license.py' in content:
                # Update references
                updated_content = content.replace(
                    'scripts/sage-license.py',
                    'tools/license/sage_license.py'
                )
                
                with open(doc_file, 'w') as f:
                    f.write(updated_content)
                
                print(f"📝 Updated {doc_file.name}")
                updates_made = True
                
        except Exception as e:
            print(f"⚠️  Could not update {doc_file}: {e}")
    
    return updates_made


def test_new_tools():
    """Test that new license tools work"""
    print("\n🧪 Testing new license tools...")
    
    project_root = Path(__file__).parent.parent
    sage_license = project_root / "tools" / "license" / "sage_license.py"
    
    if not sage_license.exists():
        print("❌ New license tools not found!")
        return False
    
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, str(sage_license), 'status'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ New license tools working correctly")
            return True
        else:
            print(f"⚠️  New tools returned error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing new tools: {e}")
        return False


def main():
    """Main migration function"""
    if not migrate_license_tools():
        sys.exit(1)
    
    if test_new_tools():
        print("\n🎯 Migration verification successful!")
    else:
        print("\n⚠️  Migration completed but tools need verification")


if __name__ == '__main__':
    main()
