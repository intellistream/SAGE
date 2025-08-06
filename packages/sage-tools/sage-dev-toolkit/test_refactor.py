#!/usr/bin/env python3
"""
Test script to verify the refactored CLI structure works correctly.
"""

import sys
from pathlib import Path

# Add the package to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from sage_dev_toolkit.cli.main import app
    from sage_dev_toolkit.cli.commands import get_apps
    
    print("✅ Successfully imported main app")
    
    # Test getting apps
    apps = get_apps()
    print(f"✅ Successfully got {len(apps)} command modules:")
    for name, app_obj in apps.items():
        commands = list(app_obj.registered_commands.keys())
        print(f"  📦 {name}: {len(commands)} commands - {', '.join(commands)}")
    
    # Test main app commands
    main_commands = list(app.registered_commands.keys())
    print(f"\n✅ Main app has {len(main_commands)} registered commands:")
    for cmd in sorted(main_commands):
        print(f"  🔧 {cmd}")
    
    print("\n🎉 CLI refactoring appears to be successful!")
    
except Exception as e:
    print(f"❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
