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

from sage_core.api.env import LocalStreamingEnvironment
from sage_core.function.source_function import SourceFunction


class ListSource(SourceFunction):
    """Simple source that emits items from a predefined list"""
    
    def __init__(self, data_list: List[Any], **kwargs):
        super().__init__(**kwargs)
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
    env = LocalStreamingEnvironment()
    
    # Example 1: Lambda List Approach
    print("\n📋 Example 1: Lambda List Approach")
    print("-" * 40)
    
    # Create test data sources
    temp_source = ListSource([20.5, 22.1, 19.8, 25.3, 21.7])
    humidity_source = ListSource([45, 52, 38, 67, 41])
    pressure_source = ListSource([1013.2, 1015.8, 1012.1, 1018.5, 1014.3])
    
    # Create streams
    temp_stream = env.from_source(temp_source)
    humidity_stream = env.from_source(humidity_source)
    pressure_stream = env.from_source(pressure_source)
    
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
    env.execute()
    
    # Example 2: Multiple Function Arguments
    print("\n📋 Example 2: Multiple Function Arguments")
    print("-" * 40)
    
    # Reset environment for new example
    env = LocalStreamingEnvironment()
    
    # Define named functions
    def format_temperature(data: float) -> str:
        celsius = data
        fahrenheit = data * 9/5 + 32
        return f"🌡️ {celsius}°C / {fahrenheit:.1f}°F"
    
    def format_humidity(data: int) -> str:
        level = "Low" if data < 40 else "High" if data > 70 else "Normal"
        return f"💧 {data}% ({level})"
    
    # Create new sources
    temp_source2 = ListSource([18.5, 26.2, 23.1, 29.8])
    humidity_source2 = ListSource([35, 75, 55, 82])
    
    # Create streams
    temp_stream2 = env.from_source(temp_source2)
    humidity_stream2 = env.from_source(humidity_source2)
    
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
    env.execute()
    
    # Example 3: Mixed Lambda and Named Functions
    print("\n📋 Example 3: Mixed Lambda and Named Functions")
    print("-" * 40)
    
    # Reset environment for new example
    env = LocalStreamingEnvironment()
    
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
    numeric_source = ManualSource([15.5, -2.3, 105.7, 42.1, 0.0])
    text_source = ManualSource(["hello", "world", "sage", "framework", "lambda"])
    boolean_source = ManualSource([True, False, True, True, False])
    
    # Create streams
    numeric_stream = env.from_source(numeric_source)
    text_stream = env.from_source(text_source)
    boolean_stream = env.from_source(boolean_source)
    
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
    env.execute()
    
    # Example 4: Mathematical Operations
    print("\n📋 Example 4: Mathematical Operations")
    print("-" * 40)
    
    # Reset environment for new example
    env = LocalStreamingEnvironment()
    
    # Create numeric data sources
    input1_source = ManualSource([1, 2, 3, 4, 5])
    input2_source = ManualSource([10, 20, 30, 40, 50])
    input3_source = ManualSource([0.1, 0.2, 0.3, 0.4, 0.5])
    
    # Create streams
    input1 = env.from_source(input1_source)
    input2 = env.from_source(input2_source)
    input3 = env.from_source(input3_source)
    
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
    env.execute()
    
    # Example 5: Error Handling and Validation
    print("\n📋 Example 5: Error Handling and Validation")
    print("-" * 40)
    
    # Reset environment for new example
    env = LocalStreamingEnvironment()
    
    # Create data with potential issues
    mixed_data1 = ManualSource([5, -3, 0, 12, -1])
    mixed_data2 = ManualSource(["valid", "", "test", None, "data"])
    
    # Create streams
    data1 = env.from_source(mixed_data1)
    data2 = env.from_source(mixed_data2)
    
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
    env.execute()
    
    print("\n✅ All CoMap lambda/callable examples completed successfully!")
    print("\n💡 Summary of supported CoMap formats:")
    print("   1. Lambda list: comap([lambda x: ..., lambda y: ...])")
    print("   2. Function arguments: comap(func1, func2, func3)")
    print("   3. Mixed types: comap([named_func, lambda x: ...])")
    print("   4. Class-based (existing): comap(MyCoMapClass)")


if __name__ == "__main__":
    main()
