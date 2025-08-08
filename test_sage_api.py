#!/usr/bin/env python3
"""
Test script to verify SAGE core API integration.
"""

def test_sage_imports():
    """Test importing core API from sage package."""
    try:
        import sage
        print(f"✅ SAGE version: {sage.__version__}")
        
        # Test core API imports
        try:
            from sage.core.api import LocalEnvironment, DataStream
            print("✅ Core API imports successful")
            
            # Test direct imports from sage package
            from sage import LocalEnvironment as SageLocalEnv
            print("✅ Direct sage imports successful")
            
        except ImportError as e:
            print(f"❌ Core API import failed: {e}")
            
    except ImportError as e:
        print(f"❌ SAGE package import failed: {e}")

def test_sage_info():
    """Test sage info functionality."""
    try:
        import sage
        print("\n" + "="*50)
        sage.info()
        print("="*50)
        
    except Exception as e:
        print(f"❌ SAGE info failed: {e}")

if __name__ == "__main__":
    print("🧪 Testing SAGE Core API Integration")
    print("-" * 40)
    
    test_sage_imports()
    test_sage_info()
    
    print("\n✅ Test completed!")
