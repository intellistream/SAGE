#!/usr/bin/env python3
"""
CoMap Lambda/Callable Support Example

This example demonstrates the new lambda and callable support for CoMap operations,
showing different ways to define multi-stream processing without requiring class definitions.
"""

import os
import sys
import time
from typing import List, Any

# Add the project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sage.core.api.local_environment import LocalEnvironment
from sage.core.function.source_function import SourceFunction


class ListSource(SourceFunction):
    """Simple source that emits items from a predefined list"""
    
    def __init__(self, data_list: List[Any],*args,  **kwargs):
        super().__init__(*args,**kwargs)
        self.data_list = data_list
        self.index = 0
    
    def execute(self) -> Any:
        if self.index < len(self.data_list):
            result = self.data_list[self.index]
            self.index += 1
            return result
        return None  # End of data


def main():
    """Demonstrate different lambda/callable usage patterns for CoMap operations"""
    
    print("🚀 CoMap Lambda/Callable Support Examples")
    print("=" * 60)
    
    # Create environment
    env1 = LocalEnvironment()
    
    # Example 1: Lambda List Approach
    print("\n📋 Example 1: Lambda List Approach")
    print("-" * 40)
    
    
    # Create streams
    temp_stream = env1.from_source(ListSource, [20.5, 22.1, 19.8, 25.3, 21.7])
    humidity_stream = env1.from_source(ListSource, [45, 52, 38, 67, 41])
    pressure_stream = env1.from_source(ListSource, [1013.2, 1015.8, 1012.1, 1018.5, 1014.3])
    
    # Apply lambda list CoMap
    result1 = (temp_stream
        .connect(humidity_stream)
        .connect(pressure_stream)
        .comap([
            lambda temp: f"🌡️ Temperature: {temp}°C ({'Hot' if temp > 23 else 'Normal'})",
            lambda humid: f"💧 Humidity: {humid}% ({'High' if humid > 60 else 'Normal'})",
            lambda press: f"🔘 Pressure: {press} hPa ({'High' if press > 1015 else 'Normal'})"
        ])
        .print("Sensor Data"))
    
    # Execute example 1
    print("Processing with lambda list...")
    env1.submit()
    env1.run_streaming()
    time.sleep(10)
    env1.stop()
    # Example 2: Multiple Function Arguments
    print("\n📋 Example 2: Multiple Function Arguments")
    print("-" * 40)
    
    # Reset environment for new example
    env2 = LocalEnvironment()
    
    # Define named functions
    def format_temperature(data: float) -> str:
        celsius = data
        fahrenheit = data * 9/5 + 32
        return f"🌡️ {celsius}°C / {fahrenheit:.1f}°F"
    
    def format_humidity(data: int) -> str:
        level = "Low" if data < 40 else "High" if data > 70 else "Normal"
        return f"💧 {data}% ({level})"
    
    # Create new sources
    temp_source2 = env2.from_source(ListSource, [18.5, 26.2, 23.1, 29.8])
    humidity_source2 = env2.from_source(ListSource, [35, 75, 55, 82])
    
    # Create streams
    temp_stream2 = temp_source2
    humidity_stream2 = humidity_source2
    
    # Apply multiple function arguments CoMap
    result2 = (temp_stream2
        .connect(humidity_stream2)
        .comap(
            format_temperature,
            format_humidity
        )
        .print("Weather Data"))
    
    # Execute example 2
    print("Processing with function arguments...")
    env2.submit()
    env2.run_streaming()
    time.sleep(10)
    env2.stop()
    
    # Example 3: Mixed Lambda and Named Functions
    print("\n📋 Example 3: Mixed Lambda and Named Functions")
    print("-" * 40)
    
    # Reset environment for new example
    env3 = LocalEnvironment()
    
    # Define a complex processing function
    def process_numeric_data(data: float) -> str:
        """Complex processing with validation"""
        if data < 0:
            return f"⚠️ Negative value: {data}"
        elif data > 100:
            return f"🔥 High value: {data}"
        else:
            return f"✅ Normal: {data:.2f}"
    
    # Create diverse data sources
    numeric_source = env3.from_source(ListSource, [15.5, -2.3, 105.7, 42.1, 0.0])
    text_source = env3.from_source(ListSource, ["hello", "world", "sage", "framework", "lambda"])
    boolean_source = env3.from_source(ListSource, [True, False, True, True, False])
    
    # Create streams
    numeric_stream = numeric_source
    text_stream = text_source
    boolean_stream = boolean_source
    
    # Apply mixed function types CoMap
    result3 = (numeric_stream
        .connect(text_stream)
        .connect(boolean_stream)
        .comap([
            process_numeric_data,  # Named function
            lambda text: f"📝 Text: '{text.upper()}'",  # Lambda function
            lambda flag: f"🚩 Status: {'✅ Enabled' if flag else '❌ Disabled'}"  # Another lambda
        ])
        .print("Mixed Data"))
    
    # Execute example 3
    print("Processing with mixed function types...")
    env3.submit()
    env3.run_streaming()
    time.sleep(10)
    env3.stop()
    
    # Example 4: Mathematical Operations
    print("\n📋 Example 4: Mathematical Operations")
    print("-" * 40)
    
    # Reset environment for new example
    env4 = LocalEnvironment()
    
    # Create numeric data sources
    input1_source = env4.from_source(ListSource, [1, 2, 3, 4, 5])
    input2_source = env4.from_source(ListSource, [10, 20, 30, 40, 50])
    input3_source = env4.from_source(ListSource, [0.1, 0.2, 0.3, 0.4, 0.5])
    
    # Create streams
    input1 = input1_source
    input2 = input2_source
    input3 = input3_source
    
    # Apply mathematical transformations
    result4 = (input1
        .connect(input2)
        .connect(input3)
        .comap(
            lambda x: x ** 2,           # Square first stream
            lambda x: x / 10,           # Divide second stream by 10
            lambda x: round(x * 100, 1) # Multiply third stream by 100 and round
        )
        .print("Math Results"))
    
    # Execute example 4
    print("Processing mathematical operations...")
    env4.submit()
    env4.run_streaming()
    time.sleep(10)
    env4.stop()
    
    # Example 5: Error Handling and Validation
    print("\n📋 Example 5: Error Handling and Validation")
    print("-" * 40)
    
    # Reset environment for new example
    env5 = LocalEnvironment()
    
    # Create data with potential issues
    mixed_data1 = env5.from_source(ListSource, [5, -3, 0, 12, -1])
    mixed_data2 = env5.from_source(ListSource, ["valid", "", "test", None, "data"])
    
    # Create streams
    data1 = mixed_data1
    data2 = mixed_data2
    
    # Apply validation and error handling
    result5 = (data1
        .connect(data2)
        .comap([
            lambda x: max(0, x) if x is not None else 0,  # Clamp negative numbers
            lambda s: s.strip() if s and isinstance(s, str) and s.strip() else "EMPTY"  # Handle empty strings
        ])
        .print("Validated Data"))
    
    # Execute example 5
    print("Processing with validation...")
    env5.submit()
    env5.run_streaming()
    time.sleep(10)
    env5.stop()
    
    print("\n✅ All CoMap lambda/callable examples completed successfully!")
    print("\n💡 Summary of supported CoMap formats:")
    print("   1. Lambda list: comap([lambda x: ..., lambda y: ...])")
    print("   2. Function arguments: comap(func1, func2, func3)")
    print("   3. Mixed types: comap([named_func, lambda x: ...])")
    print("   4. Class-based (existing): comap(MyCoMapClass)")
    
    # Clean up all environments
    print("\n🧹 Cleaning up environments...")
    env1.close()
    env2.close()
    env3.close()
    env4.close()
    env5.close()
    print("✅ All environments closed successfully!")


if __name__ == "__main__":
    main()
