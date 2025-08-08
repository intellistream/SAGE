#!/usr/bin/env python3
"""
Migration script for SAGE Queue Test Suite 2.0
Helps users migrate from the old test suite to the new pytest-based suite
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any


class TestSuiteMigrationHelper:
    """Helper for migrating to the new test suite"""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.old_files = [
            "test_basic_functionality.py",
            "test_comprehensive.py", 
            "test_multiprocess_concurrent.py",
            "test_performance_benchmark.py",
            "test_queue_functionality.py",
            "test_quick_validation.py",
            "test_ray_integration.py",
            "test_safety.py",
            "validate_test_setup.py",
            "run_all_tests.py"
        ]
        
    def check_migration_status(self) -> Dict[str, Any]:
        """Check current migration status"""
        status = {
            "new_structure_exists": self._check_new_structure(),
            "old_files_present": self._check_old_files(),
            "pytest_available": self._check_pytest(),
            "can_run_new_tests": False,
            "recommendations": []
        }
        
        # Check if new tests can run
        if status["new_structure_exists"] and status["pytest_available"]:
            status["can_run_new_tests"] = self._test_new_suite()
        
        # Generate recommendations
        status["recommendations"] = self._generate_migration_recommendations(status)
        
        return status
    
    def _check_new_structure(self) -> bool:
        """Check if new test structure exists"""
        required_files = [
            "conftest.py",
            "run_tests.py",
            "unit/__init__.py",
            "integration/__init__.py",
            "performance/__init__.py",
            "utils/__init__.py"
        ]
        
        return all((self.test_dir / f).exists() for f in required_files)
    
    def _check_old_files(self) -> List[str]:
        """Check which old files are present"""
        present = []
        for old_file in self.old_files:
            if (self.test_dir / old_file).exists():
                present.append(old_file)
        return present
    
    def _check_pytest(self) -> bool:
        """Check if pytest is available"""
        try:
            import pytest
            return True
        except ImportError:
            return False
    
    def _test_new_suite(self) -> bool:
        """Test if new suite can run basic tests"""
        try:
            cmd = [
                sys.executable, "-c",
                "import sys; sys.path.insert(0, '.'); from conftest import small_queue; print('OK')"
            ]
            result = subprocess.run(cmd, cwd=self.test_dir, capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False
    
    def _generate_migration_recommendations(self, status: Dict[str, Any]) -> List[str]:
        """Generate migration recommendations"""
        recommendations = []
        
        if not status["new_structure_exists"]:
            recommendations.append("❌ New test structure missing - run the migration setup")
        
        if not status["pytest_available"]:
            recommendations.append("📦 Install pytest: pip install pytest")
        
        if status["old_files_present"]:
            recommendations.append(f"📁 {len(status['old_files_present'])} old test files found - consider archiving")
        
        if status["can_run_new_tests"]:
            recommendations.append("✅ New test suite is ready - start using run_tests.py")
        else:
            recommendations.append("⚠️  New test suite not ready - check dependencies and setup")
        
        # Additional recommendations
        recommendations.extend([
            "📚 Read README_new.md for detailed usage instructions",
            "🔧 Install optional dependencies: pip install pytest-cov pytest-html pytest-xdist psutil",
            "🏃 Try quick validation: python run_tests.py --quick"
        ])
        
        return recommendations
    
    def backup_old_files(self, backup_dir: str = "legacy_tests") -> str:
        """Backup old test files"""
        backup_path = self.test_dir / backup_dir
        backup_path.mkdir(exist_ok=True)
        
        backed_up = []
        old_files_present = self._check_old_files()
        
        for old_file in old_files_present:
            src = self.test_dir / old_file
            dst = backup_path / old_file
            
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
                backed_up.append(old_file)
        
        # Also backup the old README if it exists
        old_readme = self.test_dir / "README.md"
        if old_readme.exists():
            backup_readme = backup_path / "README_old.md"
            if not backup_readme.exists():
                shutil.copy2(old_readme, backup_readme)
                backed_up.append("README.md")
        
        return str(backup_path), backed_up
    
    def install_dependencies(self, include_optional: bool = True) -> bool:
        """Install required and optional dependencies"""
        required_deps = ["pytest"]
        optional_deps = ["pytest-cov", "pytest-html", "pytest-xdist", "psutil"]
        
        deps_to_install = required_deps[:]
        if include_optional:
            deps_to_install.extend(optional_deps)
        
        print(f"Installing dependencies: {', '.join(deps_to_install)}")
        
        try:
            cmd = [sys.executable, "-m", "pip", "install"] + deps_to_install
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Dependencies installed successfully")
                return True
            else:
                print(f"❌ Failed to install dependencies: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error installing dependencies: {e}")
            return False
    
    def run_migration_test(self) -> bool:
        """Run a basic test to verify migration"""
        print("Running migration validation test...")
        
        try:
            cmd = [sys.executable, "run_tests.py", "--quick"]
            result = subprocess.run(cmd, cwd=self.test_dir, timeout=60)
            
            if result.returncode == 0:
                print("✅ Migration test passed")
                return True
            else:
                print("❌ Migration test failed")
                return False
        except subprocess.TimeoutExpired:
            print("❌ Migration test timed out")
            return False
        except Exception as e:
            print(f"❌ Migration test error: {e}")
            return False
    
    def print_migration_status(self, status: Dict[str, Any]):
        """Print migration status report"""
        print("\n" + "="*60)
        print("SAGE Queue Test Suite Migration Status")
        print("="*60)
        
        print("\n📋 Current Status:")
        print(f"• New test structure: {'✅ Present' if status['new_structure_exists'] else '❌ Missing'}")
        print(f"• Pytest available: {'✅ Yes' if status['pytest_available'] else '❌ No'}")
        print(f"• Old files present: {len(status['old_files_present'])} files")
        print(f"• New tests ready: {'✅ Yes' if status['can_run_new_tests'] else '❌ No'}")
        
        if status["old_files_present"]:
            print(f"\n📁 Old test files found:")
            for old_file in status["old_files_present"]:
                print(f"  • {old_file}")
        
        print(f"\n💡 Recommendations:")
        for i, rec in enumerate(status["recommendations"], 1):
            print(f"  {i}. {rec}")
        
        print("\n" + "="*60)
    
    def interactive_migration(self):
        """Interactive migration process"""
        print("SAGE Queue Test Suite Migration Assistant")
        print("="*50)
        
        # Check current status
        status = self.check_migration_status()
        self.print_migration_status(status)
        
        if status["can_run_new_tests"]:
            print("\n🎉 New test suite is already ready!")
            print("You can start using: python run_tests.py")
            return
        
        print("\n🚀 Starting migration process...")
        
        # Step 1: Install dependencies
        if not status["pytest_available"]:
            print("\n1. Installing required dependencies...")
            response = input("Install pytest and optional dependencies? [Y/n]: ").strip().lower()
            if response != 'n':
                self.install_dependencies(include_optional=True)
        
        # Step 2: Backup old files
        if status["old_files_present"]:
            print("\n2. Backing up old test files...")
            response = input("Backup old test files to legacy_tests/? [Y/n]: ").strip().lower()
            if response != 'n':
                backup_path, backed_up = self.backup_old_files()
                print(f"✅ Backed up {len(backed_up)} files to {backup_path}")
        
        # Step 3: Test migration
        print("\n3. Testing new test suite...")
        if self.run_migration_test():
            print("✅ Migration completed successfully!")
            print("\nNext steps:")
            print("• Use 'python run_tests.py' to run tests")
            print("• Read README_new.md for detailed instructions")
            print("• Consider using pytest directly for advanced features")
        else:
            print("❌ Migration test failed. Please check:")
            print("• C library is compiled (cd .. && ./build.sh)")
            print("• All dependencies are installed")
            print("• Python path includes sage_queue module")
    
    def show_usage_examples(self):
        """Show usage examples for the new test suite"""
        print("\n" + "="*60)
        print("New Test Suite Usage Examples")
        print("="*60)
        
        examples = [
            ("Quick validation", "python run_tests.py --quick"),
            ("All unit tests", "python run_tests.py --unit"),
            ("All integration tests", "python run_tests.py --integration"),
            ("Performance tests", "python run_tests.py --performance"),
            ("All tests", "python run_tests.py --all"),
            ("With coverage", "python run_tests.py --coverage"),
            ("Generate HTML report", "python run_tests.py --html"),
            ("Parallel execution", "python run_tests.py --all --parallel"),
            ("Using pytest directly", "pytest -m unit -v"),
            ("Specific test file", "pytest unit/test_basic_operations.py"),
            ("With coverage (pytest)", "pytest --cov=sage_queue --cov-report=html")
        ]
        
        for description, command in examples:
            print(f"\n{description}:")
            print(f"  {command}")
        
        print(f"\n💡 For more options, see README_new.md")
        print("="*60)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SAGE Queue Test Suite Migration Helper")
    parser.add_argument("--status", action="store_true", help="Show migration status")
    parser.add_argument("--backup", action="store_true", help="Backup old test files")
    parser.add_argument("--install-deps", action="store_true", help="Install dependencies")
    parser.add_argument("--test", action="store_true", help="Test new suite")
    parser.add_argument("--interactive", action="store_true", help="Interactive migration")
    parser.add_argument("--examples", action="store_true", help="Show usage examples")
    
    args = parser.parse_args()
    
    helper = TestSuiteMigrationHelper()
    
    if args.status:
        status = helper.check_migration_status()
        helper.print_migration_status(status)
    elif args.backup:
        backup_path, backed_up = helper.backup_old_files()
        print(f"Backed up {len(backed_up)} files to {backup_path}")
    elif args.install_deps:
        helper.install_dependencies()
    elif args.test:
        helper.run_migration_test()
    elif args.examples:
        helper.show_usage_examples()
    elif args.interactive:
        helper.interactive_migration()
    else:
        # Default: show status and offer interactive migration
        status = helper.check_migration_status()
        helper.print_migration_status(status)
        
        if not status["can_run_new_tests"]:
            print("\n🤔 Would you like to run the interactive migration?")
            response = input("Start interactive migration? [Y/n]: ").strip().lower()
            if response != 'n':
                helper.interactive_migration()
        else:
            helper.show_usage_examples()


if __name__ == "__main__":
    main()
