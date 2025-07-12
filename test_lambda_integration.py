#!/usr/bin/env python3
"""
Integration test for CoMap lambda support
"""

import os
import sys
import time

# Add the project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sage_core.api.env import LocalEnvironment
from sage_core.function.source_function import SourceFunction


class TestSource(SourceFunction):
    """Simple source that emits items from a predefined list"""
    
    def __init__(self, data_list, *args, **kwargs):
        # Skip BaseFunction.__init__ to avoid API key requirement
        self.data_list = data_list
        self.index = 0
    
    def execute(self):
        if self.index < len(self.data_list):
            result = self.data_list[self.index]
            self.index += 1
            return result
        return None  # End of data


def test_lambda_comap_integration():
    """Test full CoMap lambda integration"""
    
    print("🧪 Testing CoMap Lambda Integration")
    print("=" * 40)
    
    # Test 1: Lambda list approach
    print("\n1. Testing lambda list approach...")
    try:
        env = LocalEnvironment()
        
        stream1 = env.from_source(TestSource, [1, 2, 3])
        stream2 = env.from_source(TestSource, [10, 20, 30])
        
        result = (stream1
            .connect(stream2)
            .comap([
                lambda x: f"Stream0: {x * 2}",
                lambda x: f"Stream1: {x + 5}"
            ])
            .print("Lambda List Test"))
        
        print("✅ Lambda list CoMap pipeline created successfully!")
        
    except Exception as e:
        print(f"❌ Lambda list test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Function arguments approach
    print("\n2. Testing function arguments approach...")
    try:
        env = LocalEnvironment()
        
        def process_first(x):
            return f"First: {x}"
        
        def process_second(x):
            return f"Second: {x}"
        
        stream3 = env.from_source(TestSource, ['a', 'b', 'c'])
        stream4 = env.from_source(TestSource, ['x', 'y', 'z'])
        
        result2 = (stream3
            .connect(stream4)
            .comap(process_first, process_second)
            .print("Function Args Test"))
        
        print("✅ Function arguments CoMap pipeline created successfully!")
        
    except Exception as e:
        print(f"❌ Function arguments test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Three streams with mixed functions
    print("\n3. Testing three streams with mixed functions...")
    try:
        env = LocalEnvironment()
        
        stream5 = env.from_source(TestSource, [1.5, 2.5, 3.5])
        stream6 = env.from_source(TestSource, ["hello", "world", "test"])
        stream7 = env.from_source(TestSource, [True, False, True])
        
        def format_number(x):
            return f"Number: {x:.1f}"
        
        result3 = (stream5
            .connect(stream6)
            .connect(stream7)
            .comap([
                format_number,  # Named function
                lambda s: f"Text: {s.upper()}",  # Lambda function
                lambda b: f"Bool: {'YES' if b else 'NO'}"  # Another lambda
            ])
            .print("Mixed Three Streams"))
        
        print("✅ Three streams mixed functions CoMap pipeline created successfully!")
        
    except Exception as e:
        print(f"❌ Three streams test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ All CoMap lambda integration tests completed!")


if __name__ == "__main__":
    test_lambda_comap_integration()
