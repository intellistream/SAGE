from sage_core.environment.local_environment import LocalEnvironment
from sage_core.environment.remote_environment import RemoteEnvironment
from sage_core.function.sink_function import SinkFunction
from sage_core.function.source_function import SourceFunction
from sage_core.function.comap_function import BaseCoMapFunction
import time
import random

# 温度传感器数据源
class TemperatureSource(SourceFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
    
    def execute(self):
        self.counter += 1
        # 模拟温度数据 (18-35°C)
        temperature = round(random.uniform(18.0, 35.0), 1)
        return {'sensor_type': 'temperature', 'value': temperature, 'unit': '°C', 'id': self.counter}

# 湿度传感器数据源
class HumiditySource(SourceFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
    
    def execute(self):
        self.counter += 1
        # 模拟湿度数据 (30-90%)
        humidity = round(random.uniform(30.0, 90.0), 1)
        return {'sensor_type': 'humidity', 'value': humidity, 'unit': '%', 'id': self.counter}

# 压力传感器数据源
class PressureSource(SourceFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
    
    def execute(self):
        self.counter += 1
        # 模拟压力数据 (900-1100 hPa)
        pressure = round(random.uniform(900.0, 1100.0), 1)
        return {'sensor_type': 'pressure', 'value': pressure, 'unit': 'hPa', 'id': self.counter}

# CoMap函数：分别处理不同类型的传感器数据
class SensorDataProcessor(BaseCoMapFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.temp_alert_threshold = 30.0
        self.humidity_alert_threshold = 80.0
        self.pressure_alert_threshold = 1050.0
    
    def map0(self, data):
        """处理温度数据（来自输入流0）"""
        temp_value = data['value']
        status = "🔥 HIGH" if temp_value > self.temp_alert_threshold else "✅ Normal"
        return {
            'stream': 'temperature',
            'original': data,
            'processed_value': f"{temp_value}°C",
            'status': status,
            'alert': temp_value > self.temp_alert_threshold
        }
    
    def map1(self, data):
        """处理湿度数据（来自输入流1）"""
        humidity_value = data['value']
        status = "💧 HIGH" if humidity_value > self.humidity_alert_threshold else "✅ Normal"
        return {
            'stream': 'humidity',
            'original': data,
            'processed_value': f"{humidity_value}%",
            'status': status,
            'alert': humidity_value > self.humidity_alert_threshold
        }
    
    def map2(self, data):
        """处理压力数据（来自输入流2）"""
        pressure_value = data['value']
        status = "⚡ HIGH" if pressure_value > self.pressure_alert_threshold else "✅ Normal"
        return {
            'stream': 'pressure',
            'original': data,
            'processed_value': f"{pressure_value} hPa",
            'status': status,
            'alert': pressure_value > self.pressure_alert_threshold
        }

# 类型特定处理的CoMap函数
class TypeSpecificProcessor(BaseCoMapFunction):
    def map0(self, data):
        """简单的温度数据格式化"""
        return f"🌡️  Temperature: {data['value']}°C (ID: {data['id']})"
    
    def map1(self, data):
        """简单的湿度数据格式化"""
        return f"💧 Humidity: {data['value']}% (ID: {data['id']})"
    
    def map2(self, data):
        """简单的压力数据格式化"""
        return f"🔘 Pressure: {data['value']} hPa (ID: {data['id']})"

# 汇总输出函数
class SensorSink(SinkFunction):
    def __init__(self, **kwargs):
        self.name = kwargs.get('name', 'SensorSink')
        
    def execute(self, data):
        if isinstance(data, dict) and 'alert' in data:
            prefix = "🚨 ALERT" if data['alert'] else "📊 DATA"
            print(f"[{self.name}] {prefix}: {data['stream']} = {data['processed_value']} ({data['status']})")
        else:
            print(f"[{self.name}] {data}")
        return data

def main():
    # 创建环境
    env = RemoteEnvironment("comap_function_example")
    
    print("🚀 Starting CoMap Function Example")
    print("🌡️  Demonstrating multi-sensor data processing with CoMap")
    print("📊 Each sensor type is processed independently")
    print("⏹️  Press Ctrl+C to stop\n")
    
    # 创建不同类型的传感器数据源
    temp_stream = env.from_source(TemperatureSource, delay=1.5)
    humidity_stream = env.from_source(HumiditySource, delay=2.0)
    pressure_stream = env.from_source(PressureSource, delay=2.5)
    
    print("🔗 Creating connected streams...")
    
    # 示例1：使用CoMap进行复杂的传感器数据处理
    print("\n📈 Example 1: Advanced Sensor Processing with CoMap")
    connected_sensors = (temp_stream
        .connect(humidity_stream)
        .connect(pressure_stream)
    )
    
    # 使用CoMap分别处理每种传感器数据
    processed_result = (connected_sensors
        .comap(SensorDataProcessor)
        .sink(SensorSink, name="AdvancedProcessor")
    )
    
    # 示例2：简单的类型特定格式化
    print("📝 Example 2: Simple Type-Specific Formatting")
    simple_result = (connected_sensors
        .comap(TypeSpecificProcessor)
        .print("🎯 Formatted Output")
        
    )
    
    print("\n📈 All sensors connected and processing with CoMap...\n")
    print("💡 CoMap Features Demonstrated:")
    print("   - map0() processes temperature data independently")
    print("   - map1() processes humidity data independently") 
    print("   - map2() processes pressure data independently")
    print("   - Each stream maintains its own processing logic")
    print("   - No data merging - streams are processed separately\n")
    
    try:
        # 运行流处理
        env.submit()
        # env.run_streaming()
        time.sleep(15)  # 运行15秒以观察不同频率的数据
        
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping CoMap Function Example...")
        
    finally:
        print("\n📋 Example completed!")
        print("💡 This example demonstrated:")
        print("   - Multiple independent sensor data sources")
        print("   - CoMap function with map0, map1, map2 methods")
        print("   - Stream-specific processing logic")
        print("   - Alert detection based on sensor type")
        print("   - Independent processing without data merging")
        print("\n🔄 Comparison with regular map():")
        print("   - Regular map(): All inputs merged → single execute() method")
        print("   - CoMap: Each input stream → dedicated mapN() method")
        env.close()

if __name__ == "__main__":
    main()
