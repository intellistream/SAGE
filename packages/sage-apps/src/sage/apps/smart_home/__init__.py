"""
Smart Home System

A distributed IoT-based smart home automation system demonstrating SAGE's
interconnectivity capabilities. Manages coordinated workflows between devices
like robots, sensors, washers, and dryers.

Built on SAGE framework using stream processing operators.

Features:
- IoT device network simulation
- Automated workflows (e.g., laundry automation)
- Environment monitoring and response
- Device coordination and communication
- Event-driven automation
"""

from .pipeline import run_smart_home_demo

__all__ = ["run_smart_home_demo"]
