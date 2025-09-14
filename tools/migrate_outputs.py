#!/usr/bin/env python3
"""
SAGE Output Migration Script

This script migrates existing output files from scattered locations to the unified .sage directory.
Run this script to consolidate all logs, outputs, and temporary files.
"""

import argparse
import shutil
import sys
from pathlib import Path

try:
    from sage.common.config.output_paths import get_sage_paths, migrate_existing_outputs
except ImportError:
    print("Error: Could not import sage.common.config.output_paths")
    print("Please ensure you're running this from the SAGE project root and the package is installed.")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Migrate existing SAGE outputs to unified .sage directory"
    )
    parser.add_argument(
        "--project-root",
        type=str,
        help="Project root directory (auto-detected if not provided)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually moving files"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force migration even if files would be overwritten"
    )
    
    args = parser.parse_args()
    
    # Get SAGE paths
    sage_paths = get_sage_paths(args.project_root)
    project_root = sage_paths.project_root
    
    print(f"🏠 Project root: {project_root}")
    print(f"📁 .sage directory: {sage_paths.sage_dir}")
    print()
    
    # Define migration mappings
    migrations = [
        (project_root / "logs", sage_paths.logs_dir, "logs"),
        (project_root / "output", sage_paths.output_dir, "output"),
        (project_root / "output" / "issues-workspace", sage_paths.issues_dir / "workspace", "issues workspace"),
        (project_root / "output" / "issues-output", sage_paths.issues_dir / "output", "issues output"),
        (project_root / "output" / "issues-metadata", sage_paths.issues_dir / "metadata", "issues metadata"),
    ]
    
    # Check what needs to be migrated
    found_migrations = []
    for src, dst, name in migrations:
        if src.exists() and src != dst:
            # Count files and directories
            items = list(src.rglob('*')) if src.is_dir() else [src]
            file_count = len([f for f in items if f.is_file()])
            dir_count = len([d for d in items if d.is_dir()])
            
            found_migrations.append((src, dst, name, file_count, dir_count))
    
    if not found_migrations:
        print("✅ No migration needed. All outputs are already in the .sage directory.")
        return
    
    print("📋 Files to migrate:")
    total_files = 0
    for src, dst, name, file_count, dir_count in found_migrations:
        print(f"  📂 {name}: {src} -> {dst}")
        print(f"     📄 {file_count} files, 📁 {dir_count} directories")
        total_files += file_count
    
    print(f"\n📊 Total: {total_files} files to migrate")
    
    if args.dry_run:
        print("\n🧪 DRY RUN: No files were actually moved.")
        return
    
    if not args.force:
        response = input("\n❓ Proceed with migration? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("❌ Migration cancelled.")
            return
    
    # Perform migrations
    print("\n🚀 Starting migration...")
    
    success_count = 0
    for src, dst, name, file_count, dir_count in found_migrations:
        try:
            print(f"📁 Migrating {name}...")
            
            # Ensure destination directory exists
            dst.mkdir(parents=True, exist_ok=True)
            
            if src.is_dir():
                # Move directory contents
                for item in src.iterdir():
                    dst_item = dst / item.name
                    if item.is_dir():
                        if dst_item.exists():
                            # Merge directories
                            shutil.copytree(item, dst_item, dirs_exist_ok=True)
                            shutil.rmtree(item)
                        else:
                            shutil.move(str(item), str(dst_item))
                    else:
                        if dst_item.exists() and not args.force:
                            # Backup existing file
                            backup_name = f"{dst_item.name}.backup"
                            dst_item.rename(dst_item.parent / backup_name)
                            print(f"   ⚠️  Backed up existing file to {backup_name}")
                        shutil.move(str(item), str(dst_item))
                
                # Remove empty source directory
                try:
                    src.rmdir()
                    print(f"   🗑️  Removed empty directory {src}")
                except OSError:
                    print(f"   ⚠️  Could not remove {src} (not empty)")
            else:
                # Move single file
                if dst.exists() and not args.force:
                    backup_name = f"{dst.name}.backup"
                    dst.rename(dst.parent / backup_name)
                    print(f"   ⚠️  Backed up existing file to {backup_name}")
                shutil.move(str(src), str(dst))
            
            print(f"   ✅ Migrated {file_count} files")
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Error migrating {name}: {e}")
    
    print(f"\n🎉 Migration complete! Successfully migrated {success_count}/{len(found_migrations)} items.")
    
    # Create symlinks for backward compatibility
    if success_count > 0:
        print("\n🔗 Creating backward compatibility symlinks...")
        
        compat_links = [
            (project_root / "logs", sage_paths.logs_dir),
            (project_root / "output", sage_paths.output_dir),
        ]
        
        for link_path, target in compat_links:
            if not link_path.exists():
                try:
                    link_path.symlink_to(target, target_is_directory=True)
                    print(f"   🔗 Created symlink: {link_path} -> {target}")
                except Exception as e:
                    print(f"   ⚠️  Could not create symlink {link_path}: {e}")
    
    print(f"\n✨ All outputs are now unified under: {sage_paths.sage_dir}")
    print("🔧 Update your configurations to use the new sage.common.config.output_paths module!")


if __name__ == "__main__":
    main()