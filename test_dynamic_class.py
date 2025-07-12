#!/usr/bin/env python3
"""
Simple test for dynamic CoMap class creation
"""

import os
import sys

# Add the project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sage_core.function.comap_function import BaseCoMapFunction


def test_dynamic_class_creation():
    """Test if we can create a dynamic CoMap class"""
    
    print("🧪 Testing Dynamic CoMap Class Creation")
    print("=" * 45)
    
    # Test functions
    func1 = lambda x: f"First: {x}"
    func2 = lambda x: f"Second: {x}"
    
    # Simulate the dynamic class creation logic
    function_list = [func1, func2]
    
    # Create method definitions for dynamic class
    class_methods = {
        '__init__': lambda self: None,  # Skip BaseFunction.__init__ for testing
        'is_comap': property(lambda self: True),
        'execute': lambda self, data: self._raise_execute_error(),
        '_raise_execute_error': lambda self: self._do_raise_execute_error(),
        '_do_raise_execute_error': lambda self: (_ for _ in ()).throw(
            NotImplementedError("CoMap functions use mapN methods, not execute()")
        )
    }
    
    # Add all required mapN methods
    for i, func in enumerate(function_list):
        method_name = f"map{i}"
        # Create method that captures the function in closure
        class_methods[method_name] = (lambda f: lambda self, data: f(data))(func)
    
    # Create the dynamic class
    DynamicCoMapFunction = type(
        'DynamicCoMapFunction',
        (BaseCoMapFunction,),
        class_methods
    )
    
    print("✅ Dynamic class created successfully!")
    
    # Test instantiation
    try:
        instance = DynamicCoMapFunction()
        print("✅ Dynamic class instantiated successfully!")
        
        # Test method calls
        result1 = instance.map0("test1")
        result2 = instance.map1("test2")
        
        print(f"✅ map0 result: {result1}")
        print(f"✅ map1 result: {result2}")
        
        # Test properties
        print(f"✅ is_comap: {instance.is_comap}")
        
        # Test execute raises error
        try:
            instance.execute("should fail")
            print("❌ execute() should have raised NotImplementedError")
        except NotImplementedError:
            print("✅ execute() correctly raises NotImplementedError")
        
    except Exception as e:
        print(f"❌ Failed to instantiate or use dynamic class: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_dynamic_class_creation()
