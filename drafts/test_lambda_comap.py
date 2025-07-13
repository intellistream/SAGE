#!/usr/bin/env python3
"""
Simple test for CoMap lambda support
"""

import os
import sys
import time

# Add the project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sage_core.api.env import LocalEnvironment
from sage_core.function.source_function import SourceFunction


class ListSource(SourceFunction):
    """Simple source that emits items from a predefined list"""
    
    def __init__(self, data_list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_list = data_list
        self.index = 0
    
    def execute(self):
        if self.index < len(self.data_list):
            result = self.data_list[self.index]
            self.index += 1
            return result
        return None  # End of data


def test_lambda_comap():
    """Test basic lambda CoMap functionality"""
    
    print("🧪 Testing CoMap Lambda Support")
    print("=" * 40)
    
    # Create environment
    env = LocalEnvironment()
    
    # Create test streams
    stream1 = env.from_source(ListSource, [1, 2, 3])
    stream2 = env.from_source(ListSource, [10, 20, 30])
    
    # Test lambda list approach
    print("Testing lambda list approach...")
    try:
        result = (stream1
            .connect(stream2)
            .comap([
                lambda x: f"First: {x * 2}",
                lambda x: f"Second: {x + 5}"
            ])
            .print("Lambda Test"))
        
        print("✅ Lambda list CoMap created successfully!")
        
        # Execute
        env.submit()
        env.run_streaming() 
        time.sleep(2)
        env.stop()
        
    except Exception as e:
        print(f"❌ Lambda list test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test function arguments approach
    print("\nTesting function arguments approach...")
    env = LocalEnvironment()
    
    def process_first(x):
        return f"Func1: {x}"
    
    def process_second(x):
        return f"Func2: {x}"
    
    try:
        stream3 = env.from_source(ListSource, ['a', 'b', 'c'])
        stream4 = env.from_source(ListSource, ['x', 'y', 'z'])
        
        result2 = (stream3
            .connect(stream4)
            .comap(process_first, process_second)
            .print("Function Args Test"))
        
        print("✅ Function arguments CoMap created successfully!")
        
        # Execute
        env.submit()
        env.run_streaming()
        time.sleep(2) 
        env.stop()
        
    except Exception as e:
        print(f"❌ Function arguments test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_lambda_comap()
