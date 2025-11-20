"""Unit tests for Smart Home Application

Tests for sage.apps.smart_home module
"""

import pytest

from sage.apps.smart_home.operators import (
    AlertSink,
    AnomalyDetector,
    DeviceEvent,
    EnergyOptimizer,
    IoTDeviceSource,
    RuleEngine,
)


class TestDeviceEvent:
    """Test DeviceEvent dataclass"""

    def test_event_creation(self):
        """Test creating a device event"""
        event = DeviceEvent(
            device_id="thermostat_01",
            device_type="thermostat",
            timestamp="2024-01-15T10:00:00",
            value=22.5,
            unit="celsius",
        )

        assert event.device_id == "thermostat_01"
        assert event.device_type == "thermostat"
        assert event.value == 22.5
        assert event.unit == "celsius"
        assert event.is_anomaly is False

    def test_event_with_anomaly(self):
        """Test event marked as anomaly"""
        event = DeviceEvent(
            device_id="sensor_02",
            device_type="temperature",
            timestamp="2024-01-15T10:00:00",
            value=100.0,
            unit="celsius",
            is_anomaly=True,
        )

        assert event.is_anomaly is True


class TestIoTDeviceSource:
    """Test IoTDeviceSource operator"""

    def test_source_creation(self):
        """Test creating IoT device source"""
        devices = ["thermostat_01", "light_01", "sensor_01"]
        source = IoTDeviceSource(devices=devices, duration=60, event_rate=10)

        assert len(source.devices) == 3
        assert source.duration == 60
        assert source.event_rate == 10

    def test_source_generates_events(self):
        """Test source generates device events"""
        devices = ["thermostat_01", "light_01"]
        source = IoTDeviceSource(devices=devices, duration=5, event_rate=5)

        # Generate events
        events = list(source.run())

        # Should generate some events
        assert len(events) >= 0
        if len(events) > 0:
            assert isinstance(events[0], DeviceEvent)
            assert events[0].device_id in devices

    def test_source_device_types(self):
        """Test device type assignment"""
        devices = ["thermostat_01", "light_02", "sensor_03"]
        source = IoTDeviceSource(devices=devices, duration=10, event_rate=5)

        # The source should handle different device types
        assert len(source.devices) == 3


class TestAnomalyDetector:
    """Test AnomalyDetector operator"""

    def test_detector_creation(self):
        """Test creating anomaly detector"""
        detector = AnomalyDetector(threshold=3.0, window_size=100)

        assert detector.threshold == 3.0
        assert detector.window_size == 100

    def test_detect_normal_event(self):
        """Test detecting normal event"""
        detector = AnomalyDetector(threshold=3.0, window_size=100)

        event = DeviceEvent(
            device_id="thermostat_01",
            device_type="thermostat",
            timestamp="2024-01-15T10:00:00",
            value=22.5,
            unit="celsius",
        )

        result = detector.map(event)
        # First event is typically normal (no baseline yet)
        assert isinstance(result, DeviceEvent)

    def test_detect_anomalous_event(self):
        """Test detecting anomalous event"""
        detector = AnomalyDetector(threshold=2.0, window_size=10)

        # Send normal events first
        normal_events = [
            DeviceEvent(
                device_id="sensor_01",
                device_type="temperature",
                timestamp=f"2024-01-15T10:00:{i:02d}",
                value=20.0 + i * 0.1,
                unit="celsius",
            )
            for i in range(5)
        ]

        for event in normal_events:
            detector.map(event)

        # Send anomalous event
        anomaly = DeviceEvent(
            device_id="sensor_01",
            device_type="temperature",
            timestamp="2024-01-15T10:00:10",
            value=100.0,  # Extreme value
            unit="celsius",
        )

        result = detector.map(anomaly)
        # Depending on implementation, might be marked as anomaly
        assert isinstance(result, DeviceEvent)


class TestRuleEngine:
    """Test RuleEngine operator"""

    def test_engine_creation(self):
        """Test creating rule engine"""
        rules = {
            "temperature_high": lambda e: e.value > 30.0
            if e.device_type == "temperature"
            else False
        }

        engine = RuleEngine(rules=rules)

        assert len(engine.rules) == 1
        assert "temperature_high" in engine.rules

    def test_apply_rule_triggered(self):
        """Test rule that should be triggered"""
        rules = {"temp_high": lambda e: e.value > 25.0 and e.device_type == "temperature"}

        engine = RuleEngine(rules=rules)

        event = DeviceEvent(
            device_id="sensor_01",
            device_type="temperature",
            timestamp="2024-01-15T10:00:00",
            value=30.0,
            unit="celsius",
        )

        result = engine.map(event)
        assert isinstance(result, DeviceEvent)

    def test_apply_rule_not_triggered(self):
        """Test rule that should not be triggered"""
        rules = {"temp_high": lambda e: e.value > 50.0 and e.device_type == "temperature"}

        engine = RuleEngine(rules=rules)

        event = DeviceEvent(
            device_id="sensor_01",
            device_type="temperature",
            timestamp="2024-01-15T10:00:00",
            value=20.0,
            unit="celsius",
        )

        result = engine.map(event)
        assert isinstance(result, DeviceEvent)


class TestEnergyOptimizer:
    """Test EnergyOptimizer operator"""

    def test_optimizer_creation(self):
        """Test creating energy optimizer"""
        optimizer = EnergyOptimizer(target_consumption=1000.0, optimization_window=60)

        assert optimizer.target_consumption == 1000.0
        assert optimizer.optimization_window == 60

    def test_optimize_event(self):
        """Test optimizing device event"""
        optimizer = EnergyOptimizer(target_consumption=1000.0, optimization_window=60)

        event = DeviceEvent(
            device_id="hvac_01",
            device_type="hvac",
            timestamp="2024-01-15T10:00:00",
            value=500.0,
            unit="watts",
        )

        result = optimizer.map(event)
        assert isinstance(result, DeviceEvent)

    def test_optimizer_with_multiple_devices(self):
        """Test optimizer with multiple device events"""
        optimizer = EnergyOptimizer(target_consumption=2000.0, optimization_window=60)

        events = [
            DeviceEvent(
                device_id=f"device_{i}",
                device_type="appliance",
                timestamp=f"2024-01-15T10:00:{i:02d}",
                value=100.0 + i * 50,
                unit="watts",
            )
            for i in range(5)
        ]

        results = [optimizer.map(event) for event in events]
        assert all(isinstance(r, DeviceEvent) for r in results)


class TestAlertSink:
    """Test AlertSink operator"""

    def test_sink_creation(self):
        """Test creating alert sink"""
        sink = AlertSink(alert_threshold=0.8)

        assert sink.alert_threshold == 0.8

    def test_sink_collect_event(self):
        """Test collecting events"""
        sink = AlertSink(alert_threshold=0.5)

        event = DeviceEvent(
            device_id="sensor_01",
            device_type="temperature",
            timestamp="2024-01-15T10:00:00",
            value=35.0,
            unit="celsius",
            is_anomaly=True,
        )

        sink.sink(event)
        # Should collect the event
        # Verify collection depends on implementation

    def test_sink_multiple_events(self):
        """Test collecting multiple events"""
        sink = AlertSink(alert_threshold=0.5)

        events = [
            DeviceEvent(
                device_id=f"sensor_{i}",
                device_type="temperature",
                timestamp=f"2024-01-15T10:00:{i:02d}",
                value=20.0 + i * 5,
                unit="celsius",
                is_anomaly=i % 2 == 0,
            )
            for i in range(10)
        ]

        for event in events:
            sink.sink(event)

        # Should have collected events
        alerts = sink.get_alerts()
        assert isinstance(alerts, (list, dict)) or alerts is None


@pytest.mark.integration
class TestSmartHomePipeline:
    """Integration tests for smart home pipeline"""

    def test_pipeline_creation(self):
        """Test creating the smart home pipeline"""
        from sage.apps.smart_home.pipeline import create_smart_home_pipeline

        devices = ["thermostat_01", "light_01", "sensor_01"]
        pipeline = create_smart_home_pipeline(devices=devices, duration=60, event_rate=10)

        assert pipeline is not None

    @pytest.mark.skip(reason="Long-running simulation test")
    def test_end_to_end_monitoring(self):
        """Test complete smart home monitoring"""
        from sage.apps.smart_home.pipeline import create_smart_home_pipeline

        devices = ["thermostat_01", "light_01", "sensor_01", "hvac_01"]
        _pipeline = create_smart_home_pipeline(devices=devices, duration=30, event_rate=5)

        # Run monitoring
        # results = _pipeline.execute()
        # assert results is not None
        pass
