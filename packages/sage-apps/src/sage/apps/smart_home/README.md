# Smart Home System

A distributed IoT-based smart home automation system built on SAGE framework demonstrating
interconnectivity and coordination capabilities across multiple devices.

## Features

- **IoT Device Network**: Simulates various smart home devices (robots, sensors, appliances)
- **Automated Workflows**: Coordinates complex multi-device workflows using SAGE operators
- **Environment Monitoring**: Real-time sensor data collection and response
- **Event-Driven Architecture**: Devices communicate through SAGE stream processing
- **Device Coordination**: Manages dependencies and sequencing with MapFunction chains

## Quick Start

```python
from sage.apps.smart_home import run_smart_home_demo

# Run single laundry automation cycle
run_smart_home_demo()

# Run multiple cycles
run_smart_home_demo(num_cycles=3)

# Verbose mode with event logging
run_smart_home_demo(num_cycles=2, verbose=True)
```

## Command Line Usage

```bash
# Run default (1 cycle)
python -m sage.apps.smart_home.pipeline

# Run multiple cycles
python -m sage.apps.smart_home.pipeline --cycles 3

# Verbose mode
python -m sage.apps.smart_home.pipeline --verbose
```

## Pipeline Architecture

The system uses SAGE stream processing operators:

```
LaundryWorkflowSource (BatchFunction)
    ↓
DeviceExecutor (MapFunction)
    ↓
EnvironmentMonitor (MapFunction)
    ↓
WorkflowProgressSink (SinkFunction)
    ↓
EventLogSink (SinkFunction) [optional]
```

### Operators

- **LaundryWorkflowSource**: Generates workflow tasks (check env → collect → wash → transfer → dry →
  store)
- **DeviceExecutor**: Executes tasks on simulated IoT devices (robot, washer, dryer, sensors)
- **EnvironmentMonitor**: Monitors and validates environmental conditions
- **WorkflowProgressSink**: Tracks and reports workflow progress
- **EventLogSink**: Logs all device events for auditing

## Devices

### Robot (🤖)

- **Purpose**: Move items between locations
- **Commands**: `move_laundry`
- **Events**: `task_completed`

### Washer (🧺)

- **Purpose**: Wash laundry
- **Commands**: `start_wash`
- **Events**: `wash_completed`

### Dryer (💨)

- **Purpose**: Dry laundry
- **Commands**: `start_dry`
- **Events**: `dry_completed`

### Humidity Sensor (📊)

- **Purpose**: Monitor humidity levels
- **Commands**: `read`
- **Events**: `reading`
- **Range**: 30-80%

### Motion Sensor (👁️)

- **Purpose**: Detect motion
- **Commands**: `detect`
- **Events**: `motion_detected`, `no_motion`

## Automated Workflows

### Laundry Automation

Complete end-to-end laundry automation:

1. **Environment Check**: Monitor humidity and conditions
1. **Collection**: Robot picks up laundry from basket
1. **Washing**: Washer runs complete wash cycle
1. **Transfer**: Robot moves laundry to dryer
1. **Drying**: Dryer runs complete dry cycle
1. **Storage**: Robot moves laundry to drying rack

```python
home = SmartHomeSystem()
home.laundry_automation_workflow()
```

### Custom Workflows

Create your own automation:

```python
# Send custom commands
home.send_command("robot_001", "move_laundry", {
    "from": "basket",
    "to": "washer"
})

home.send_command("washer_001", "start_wash")
```

## Architecture

### Event-Driven Communication

Devices communicate through events:

```
Sensor Reading → Event → Automation Rule → Device Command → Action
```

### Device Coordination

The system coordinates multiple devices:

```
Robot → Washer → Robot → Dryer → Robot
  |        |       |       |       |
  v        v       v       v       v
Event → Event → Event → Event → Event
```

## Example Output

```
======================================================================
Smart Home Laundry Automation Workflow
======================================================================

[Step 1] Checking environmental conditions...
  📊 Humidity: 45.3%

[Step 2] Robot collecting laundry...
  🤖 Robot robot_001: Moving laundry from basket to washer

[Step 3] Washing laundry...
  🧺 Washer washer_001: Starting wash cycle
  ✓ Washer washer_001: Wash cycle completed

[Step 4] Robot moving laundry to dryer...
  🤖 Robot robot_001: Moving laundry from washer to dryer

[Step 5] Drying laundry...
  💨 Dryer dryer_001: Starting dry cycle
  ✓ Dryer dryer_001: Dry cycle completed

[Step 6] Robot moving laundry to drying rack...
  🤖 Robot robot_001: Moving laundry from dryer to drying_rack

======================================================================
✓ Laundry automation workflow completed successfully!
======================================================================
```

## Use Cases

- **Home Automation**: Automated household tasks
- **IoT Coordination**: Multi-device workflows
- **Smart Building**: Building management systems
- **Industrial IoT**: Factory automation
- **Energy Management**: Optimize resource usage

## Testing

Run the example script:

```bash
python examples/apps/run_smart_home.py
```

Run with specific workflow:

```bash
python examples/apps/run_smart_home.py --workflow laundry
python examples/apps/run_smart_home.py --workflow monitoring
```

## Configuration

Devices can be configured with custom parameters:

```python
# Custom cycle times
washer = Washer("washer_001")
washer.cycle_time = 5  # seconds

# Custom thresholds
humidity_sensor = HumiditySensor("humid_001")
```

## Dependencies

- Python 3.8+
- Standard library only
- Optional: SAGE framework for distributed processing

## Future Enhancements

- Real IoT device integration (MQTT, CoAP)
- Machine learning for predictive automation
- Voice control integration
- Mobile app interface
- Energy optimization algorithms
- Multi-home coordination
- Cloud integration for remote control
