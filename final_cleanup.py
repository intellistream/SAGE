#!/usr/bin/env python3
"""
Final root directory cleanup script for SAGE Development Toolkit.

This script integrates remaining development tools and archives old scripts.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def main():
    """Main cleanup function."""
    project_root = Path(__file__).parent
    archive_dir = project_root / "archive"
    
    print("🧹 Starting final root directory cleanup...")
    
    # Files to archive (no longer needed in root)
    files_to_archive = [
        "cleanup_root_directory.py",
        "sage_dev_toolkit.py",  # We have the package now
    ]
    
    # Create archive structure if needed
    tools_archive = archive_dir / "tools"
    tools_archive.mkdir(parents=True, exist_ok=True)
    
    # Archive remaining development files
    archived_count = 0
    for file_name in files_to_archive:
        file_path = project_root / file_name
        if file_path.exists():
            print(f"📦 Archiving {file_name}...")
            shutil.move(str(file_path), str(tools_archive / file_name))
            archived_count += 1
    
    # Update migration summary
    migration_summary = archive_dir / "MIGRATION_SUMMARY.md"
    
    # Append to existing summary
    with open(migration_summary, "a", encoding="utf-8") as f:
        f.write(f"\n## Final Cleanup - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("### Additional Files Archived\n\n")
        
        for file_name in files_to_archive:
            if (project_root / file_name).exists() or (tools_archive / file_name).exists():
                f.write(f"- `{file_name}` → `archive/tools/{file_name}`\n")
        
        f.write(f"\n### New Dev-Toolkit Features\n\n")
        f.write("Added to SAGE Development Toolkit:\n")
        f.write("- **Commercial Package Manager**: `sage-dev commercial`\n")
        f.write("- **Dependency Analyzer**: `sage-dev dependencies`\n") 
        f.write("- **Class Dependency Checker**: `sage-dev classes`\n")
        f.write("\n")
        f.write("These tools provide comprehensive analysis and management capabilities:\n")
        f.write("- Commercial SAGE package management\n")
        f.write("- Project-wide dependency analysis and health checking\n")
        f.write("- Class-level dependency tracking and visualization\n")
        f.write("\n")
    
    # Create a simple root entry point if needed
    root_entry = project_root / "sage_dev.py"
    if not root_entry.exists():
        with open(root_entry, "w", encoding="utf-8") as f:
            f.write('''#!/usr/bin/env python3
"""
Simple entry point for SAGE Development Toolkit.

This script provides quick access to the dev-toolkit from the project root.
For full functionality, install the package: pip install -e dev-toolkit/
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Run sage-dev toolkit."""
    project_root = Path(__file__).parent
    dev_toolkit_path = project_root / "dev-toolkit"
    
    if not dev_toolkit_path.exists():
        print("❌ dev-toolkit directory not found!")
        sys.exit(1)
    
    # Try to run the installed package first
    try:
        subprocess.run([sys.executable, "-m", "sage_dev_toolkit"] + sys.argv[1:])
    except FileNotFoundError:
        print("⚠️  SAGE Dev Toolkit not installed.")
        print("🔧 Install with: pip install -e dev-toolkit/")
        print("📖 Or see dev-toolkit/README.md for setup instructions")
        sys.exit(1)

if __name__ == "__main__":
    main()
''')
        print(f"✅ Created simple entry point: sage_dev.py")
    
    # Final status report
    print(f"\n🎉 Final cleanup completed!")
    print(f"📦 Archived {archived_count} additional files")
    print(f"🛠️  Root directory is now clean and organized")
    
    # Show current root status
    print(f"\n📁 Current root directory contents:")
    root_items = []
    for item in sorted(project_root.iterdir()):
        if item.name.startswith('.'):
            continue
        if item.is_dir():
            root_items.append(f"📁 {item.name}/")
        else:
            root_items.append(f"📄 {item.name}")
    
    for item in root_items[:15]:  # Show first 15 items
        print(f"   {item}")
    
    if len(root_items) > 15:
        print(f"   ... and {len(root_items) - 15} more items")
    
    print(f"\n✨ SAGE Development Toolkit integration complete!")
    print(f"🚀 Use 'sage-dev --help' to explore all available tools")

if __name__ == "__main__":
    main()
