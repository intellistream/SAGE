# 分布式智能家居系统

基于 SAGE 框架构建的 IoT 智能家居自动化系统，展示设备间的协调和自动化工作流。

## 概述

智能家居系统演示了 SAGE 在 IoT 设备协调和事件驱动架构方面的能力。通过模拟多个智能设备（机器人、洗衣机、烘干机、传感器）的协同工作，展示了完整的自动化洗衣工作流程。

## 核心功能

### 1. IoT 设备模拟

- 🤖 智能机器人 - 物品搬运
- 🧺 洗衣机 - 清洗衣物
- 💨 烘干机 - 烘干衣物
- 📊 湿度传感器 - 环境监测
- 👁️ 运动传感器 - 活动检测

### 2. 自动化工作流

**洗衣自动化流程**：

1. 检查环境条件（湿度等）
1. 机器人从篮子中收集衣物
1. 将衣物放入洗衣机
1. 洗衣机运行洗涤程序
1. 机器人将衣物转移到烘干机
1. 烘干机运行烘干程序
1. 机器人将衣物放到晾衣架

### 3. 设备协调

- 任务依赖管理
- 顺序执行控制
- 事件驱动通信
- 状态同步

## 技术架构

### SAGE 算子管道

```
LaundryWorkflowSource (BatchFunction)
    ↓
DeviceExecutor (MapFunction)
    ↓
EnvironmentMonitor (MapFunction)
    ↓
WorkflowProgressSink (SinkFunction)
```

### 算子说明

| 算子                  | 类型          | 功能                 |
| --------------------- | ------------- | -------------------- |
| LaundryWorkflowSource | BatchFunction | 生成工作流任务序列   |
| DeviceExecutor        | MapFunction   | 在设备上执行任务     |
| EnvironmentMonitor    | MapFunction   | 监控环境条件         |
| WorkflowProgressSink  | SinkFunction  | 跟踪流程进度         |
| EventLogSink          | SinkFunction  | 记录所有事件（可选） |

## 使用方法

### 基本使用

```python
from sage.apps.smart_home import run_smart_home_demo

# 运行单次洗衣流程
run_smart_home_demo()
```

### 运行多个周期

```python
# 运行 3 个洗衣周期
run_smart_home_demo(num_cycles=3, verbose=True)
```

### 命令行使用

```bash
# 默认（1 个周期）
python -m sage.apps.smart_home.pipeline

# 多个周期
python -m sage.apps.smart_home.pipeline --cycles 3

# 详细模式
python -m sage.apps.smart_home.pipeline --cycles 2 --verbose

# 使用示例脚本
python examples/apps/run_smart_home.py --cycles 3
```

## 输出示例

```
🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠
               SAGE Smart Home Automation Demo
🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠🏠

======================================================================
🔄 Automated Laundry Workflow
======================================================================
   Steps:
   1. Check environmental conditions (humidity)
   2. Robot collects laundry from basket
   3. Washer runs wash cycle
   4. Robot moves laundry to dryer
   5. Dryer runs dry cycle
   6. Robot moves laundry to drying rack
======================================================================

🚀 Starting smart home automation...

📊 humid_sensor_001: Check humidity and environment
   📊 Current humidity: 52.3%
🤖 robot_001: Robot collects laundry from basket
🧺 washer_001: Wash laundry
🤖 robot_001: Robot moves laundry to dryer
💨 dryer_001: Dry laundry
🤖 robot_001: Robot moves laundry to drying rack
✓ Cycle 1 completed (6/6 steps)

======================================================================
✅ Smart Home Workflow Summary
======================================================================
   Total tasks completed: 6
   Total time: 6.23s
   Average time per task: 1.04s
======================================================================
```

## 应用场景

### 家庭自动化

- 洗衣流程自动化
- 清洁机器人调度
- 环境控制

### 智能建筑

- 能源管理
- 安防系统
- 设备维护

### 工业 IoT

- 生产线协调
- 设备监控
- 预测性维护

## 扩展功能

### 添加新设备

```python
from sage.apps.smart_home.operators import SmartDevice, DeviceType

class AirConditioner(SmartDevice):
    def __init__(self, device_id: str):
        super().__init__(device_id, DeviceType.AC)

    def process_command(self, command):
        if command.command == "set_temperature":
            temperature = command.parameters.get("temp")
            # 执行温控逻辑
            ...
```

### 自定义工作流

```python
# 创建自定义工作流任务
custom_workflow = [
    {"task": "turn_on_lights", "device": "light_001"},
    {"task": "adjust_temperature", "device": "ac_001"},
    {"task": "start_music", "device": "speaker_001"},
]
```

### 条件规则（Future）

```python
# 基于传感器数据的自动化规则
if humidity > 70:
    turn_on_dehumidifier()
if motion_detected and time > 22:00:
    turn_on_security_mode()
```

## 技术细节

### 设备通信

- 事件驱动架构
- 异步任务处理
- 状态同步机制

### 工作流管理

- 任务依赖图
- 顺序执行保证
- 错误恢复（Future）

### 性能优化

- 并行任务执行（Future）
- 设备状态缓存
- 网络优化

## 相关资源

- [源代码](https://github.com/intellistream/SAGE/tree/main/packages/sage-apps/src/sage/apps/smart_home)
- [示例脚本](https://github.com/intellistream/SAGE/tree/main/examples/apps/run_smart_home.py)
- [IoT 最佳实践](best-practices/index.md)

## 下一步

- 尝试 [文章监控系统](article-monitoring.md)
- 探索 [自动扩缩容系统](auto-scaling-chat.md)
- 查看更多 [应用示例](applications.md)
