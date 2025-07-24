#!/usr/bin/env python3
"""
Minimal test to identify virtual method issue
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'build'))

try:
    import sage_flow_py
    print("✅ Successfully imported sage_flow_py")
except ImportError as e:
    print(f"❌ Failed to import sage_flow_py: {e}")
    sys.exit(1)

def minimal_test():
    """Minimal test to isolate the issue"""
    print("\n🔍 Minimal Memory Pool Test:")
    print("=" * 35)
    
    try:
        print("  Step 1: Creating memory pool...")
        memory_pool = sage_flow_py.create_default_memory_pool()
        print(f"  ✅ Memory pool created: {type(memory_pool)}")
        
        print("  Step 2: Check if we can access the object...")
        print(f"  ✅ Object accessible: {memory_pool}")
        
        print("  Step 3: Testing get_allocated_size() method...")
        # This is where the crash might occur
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Minimal Virtual Method Test")
    print("===============================")
    
    minimal_test()
    
    print("\n✨ Test completed!")
