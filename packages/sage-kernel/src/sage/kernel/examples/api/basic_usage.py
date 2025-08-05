"""
Example: Basic SAGE Kernel API Usage

This example demonstrates how to use the basic SAGE Kernel APIs
for creating and executing simple data processing tasks.
"""

from sage.api.function.base_function import BaseFunction
from sage.api.local_environment import LocalEnvironment
from sage.api.datastream import DataStream

class SimpleMapFunction(BaseFunction):
    """A simple map function that doubles input values"""
    
    def process(self, data):
        """Double the input value"""
        return data * 2

def main():
    """Main example function"""
    print("SAGE Kernel API Example - Basic Usage")
    
    # Create a local environment
    env = LocalEnvironment()
    
    # Create a simple data stream
    data = [1, 2, 3, 4, 5]
    stream = DataStream(data)
    
    # Apply transformation
    map_func = SimpleMapFunction()
    result = stream.map(map_func)
    
    print(f"Original data: {data}")
    print(f"Transformed data: {result}")

if __name__ == "__main__":
    main()
