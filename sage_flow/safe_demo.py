#!/usr/bin/env python3
"""
Safe demonstration of SAGE Flow Environment System
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

def test_basic_functionality():
    """Test basic functionality without potential crashes"""
    print("\n🧪 Basic Functionality Test:")
    print("=" * 40)
    
    try:
        # Test 1: Memory pool creation
        print("  Testing memory pool creation...")
        memory_pool = sage_flow_py.create_default_memory_pool()
        print(f"  ✅ Memory pool created: {type(memory_pool)}")
        
        # Test memory pool methods safely
        print("  Testing memory pool methods...")
        allocated_size = memory_pool.get_allocated_size()
        print(f"  ✅ Allocated size: {allocated_size}")
        
        # Test 2: Environment creation
        print("  Testing environment creation...")
        env = sage_flow_py.SageFlowEnvironment("test_job")
        print(f"  ✅ Environment created: {type(env)}")
        
        # Test 3: Configuration
        print("  Testing configuration...")
        config = sage_flow_py.EnvironmentConfig()
        
        # Use the correct property names from the C++ struct
        config.properties_["batch_size"] = "32"
        config.properties_["parallelism"] = "4"
        print(f"  ✅ Config created with properties: {dict(config.properties_)}")
        
        # Test 4: Memory configuration (safer approach)
        print("  Testing memory configuration...")
        memory_config = {
            "collection_name": "test_collection",
            "vector_dimension": "768",  # Convert to string
            "index_type": "HNSW",
            "metric": "cosine"
        }
        
        # Just test the method call without complex operations
        env.set_memory(memory_config)
        print("  ✅ Memory configuration set successfully")
        
        print("\n🎉 All basic tests passed!")
        
    except Exception as e:
        print(f"  ❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

def test_index_creation():
    """Test index creation functionality"""
    print("\n📚 Index Creation Test:")
    print("=" * 30)
    
    try:
        # Create memory pool first
        memory_pool = sage_flow_py.create_default_memory_pool()
        print("  ✅ Memory pool created for index")
        
        # Test different index types
        index_types = ["BRUTE_FORCE", "HNSW", "IVF"]
        
        for index_type in index_types:
            try:
                print(f"  Testing {index_type} index creation...")
                index_type_enum = getattr(sage_flow_py.IndexType, index_type)
                index = sage_flow_py.create_index(index_type_enum, memory_pool)
                print(f"  ✅ {index_type} index created: {type(index)}")
            except Exception as e:
                print(f"  ⚠️  {index_type} index creation failed: {e}")
                
    except Exception as e:
        print(f"  ❌ Index test error: {e}")

if __name__ == "__main__":
    print("🔬 SAGE Flow Safe Demonstration")
    print("================================")
    
    test_basic_functionality()
    test_index_creation()
    
    print("\n✨ Safe demonstration completed!")
