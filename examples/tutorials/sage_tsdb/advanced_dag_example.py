"""
Advanced SAGE TSDB DAG Example

This example demonstrates advanced features:
1. Multi-sensor data ingestion
2. Complex window aggregations
3. Real-time anomaly detection
4. Integration with SAGE service layer
"""

from datetime import datetime
from typing import Any, Dict, List

import numpy as np

from sage.middleware.components.sage_tsdb import (
    SageTSDB,
    SageTSDBService,
    TimeRange,
    WindowAggregator,
)
from sage.libs.rag.local_env import LocalEnvironment
from sage.libs.rag.node import MapFunction, SinkFunction, SourceFunction


class MultiSensorSource(SourceFunction):
    """Generate data from multiple sensors"""

    def __init__(self, num_sensors: int = 3, points_per_sensor: int = 30):
        super().__init__()
        self.num_sensors = num_sensors
        self.points_per_sensor = points_per_sensor
        self.base_time = int(datetime.now().timestamp() * 1000)

    def generate(self) -> List[Dict[str, Any]]:
        """Generate multi-sensor data"""
        data_points = []

        for sensor_id in range(self.num_sensors):
            for i in range(self.points_per_sensor):
                timestamp = self.base_time + i * 1000
                # Different patterns for different sensors
                if sensor_id == 0:
                    value = 20 + 5 * np.sin(i * 0.2) + np.random.randn()
                elif sensor_id == 1:
                    value = 30 + 3 * np.cos(i * 0.15) + np.random.randn() * 0.5
                else:
                    value = 25 + 2 * np.sin(i * 0.25) + np.random.randn() * 1.5

                data_points.append(
                    {
                        "timestamp": timestamp,
                        "value": value,
                        "sensor_id": f"sensor_{sensor_id:02d}",
                        "location": f"room_{sensor_id % 3}",
                        "type": "temperature",
                    }
                )

        return data_points


class AnomalyDetector(MapFunction):
    """Detect anomalies in time series data"""

    def __init__(self, db: SageTSDB, threshold_std: float = 2.5):
        super().__init__()
        self.db = db
        self.threshold_std = threshold_std

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect anomalies based on historical statistics"""
        # Query historical data
        time_range = TimeRange(
            start_time=data["timestamp"] - 30000,  # Last 30 seconds
            end_time=data["timestamp"],
        )

        historical = self.db.query(
            time_range=time_range, tags={"sensor_id": data["sensor_id"]}
        )

        is_anomaly = False
        anomaly_score = 0.0

        if len(historical) > 5:  # Need enough data
            values = [h.value for h in historical]
            mean = np.mean(values)
            std = np.std(values)

            if std > 0:
                z_score = abs((data["value"] - mean) / std)
                is_anomaly = z_score > self.threshold_std
                anomaly_score = z_score

        return {
            **data,
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score,
            "historical_count": len(historical),
        }


class AggregationNode(MapFunction):
    """Perform window-based aggregations"""

    def __init__(self, db: SageTSDB):
        super().__init__()
        self.db = db
        self.aggregators = {
            "avg": WindowAggregator(
                {"window_type": "tumbling", "window_size": 10000, "aggregation": "avg"}
            ),
            "max": WindowAggregator(
                {"window_type": "tumbling", "window_size": 10000, "aggregation": "max"}
            ),
        }
        self.processed_count = 0

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate data periodically"""
        self.processed_count += 1

        # Aggregate every 10 points
        if self.processed_count % 10 == 0:
            # Query recent data
            time_range = TimeRange(
                start_time=data["timestamp"] - 30000, end_time=data["timestamp"]
            )

            recent_data = self.db.query(
                time_range=time_range, tags={"sensor_id": data["sensor_id"]}
            )

            # Apply aggregations
            aggregations = {}
            for agg_name, aggregator in self.aggregators.items():
                agg_result = aggregator.process(recent_data)
                aggregations[agg_name] = (
                    [{"timestamp": r.timestamp, "value": r.value} for r in agg_result]
                    if agg_result
                    else []
                )

            return {
                **data,
                "aggregations": aggregations,
                "aggregation_stats": {
                    name: agg.get_stats() for name, agg in self.aggregators.items()
                },
            }

        return data


class AnalyticsSink(SinkFunction):
    """Print analytics results"""

    def __init__(self):
        super().__init__()
        self.anomaly_count = 0
        self.total_count = 0

    def execute(self, data: Dict[str, Any]) -> None:
        """Print results and track statistics"""
        self.total_count += 1

        # Track anomalies
        if data.get("is_anomaly", False):
            self.anomaly_count += 1
            print(f"\n{'!' * 60}")
            print(f"ANOMALY DETECTED!")
            print(f"{'!' * 60}")
            print(f"Sensor: {data['sensor_id']}")
            print(f"Timestamp: {data['timestamp']}")
            print(f"Value: {data['value']:.2f}")
            print(f"Anomaly Score: {data['anomaly_score']:.2f}")
            print(f"Historical Count: {data['historical_count']}")

        # Print aggregations
        if "aggregations" in data:
            print(f"\n{'=' * 60}")
            print(f"Aggregation Results for {data['sensor_id']}")
            print(f"{'=' * 60}")

            for agg_name, agg_data in data["aggregations"].items():
                print(f"\n{agg_name.upper()} Aggregation:")
                for window in agg_data[-3:]:  # Show last 3 windows
                    print(
                        f"  Timestamp: {window['timestamp']}, Value: {window['value']:.2f}"
                    )

        # Periodic summary
        if self.total_count % 50 == 0:
            print(f"\n{'=' * 60}")
            print(f"Analytics Summary (Total: {self.total_count})")
            print(f"{'=' * 60}")
            print(f"Total Processed: {self.total_count}")
            print(f"Anomalies Detected: {self.anomaly_count}")
            if self.total_count > 0:
                print(
                    f"Anomaly Rate: {self.anomaly_count / self.total_count * 100:.2f}%"
                )


def example_advanced_analytics_dag():
    """Advanced analytics pipeline with multiple features"""
    print("\n" + "=" * 60)
    print("Advanced Analytics DAG Example")
    print("=" * 60)

    # Create TSDB instance
    db = SageTSDB()

    # Create environment
    env = LocalEnvironment()

    # Build comprehensive pipeline
    (
        env.from_source(MultiSensorSource(num_sensors=3, points_per_sensor=40))
        .flat_map(lambda data_list: data_list)
        .map(
            lambda data: {
                **data,
                "index": db.add(
                    timestamp=data["timestamp"],
                    value=data["value"],
                    tags={
                        "sensor_id": data["sensor_id"],
                        "location": data["location"],
                        "type": data["type"],
                    },
                ),
            }
        )  # Ingest
        .map(AnomalyDetector(db, threshold_std=2.0))  # Detect anomalies
        .map(AggregationNode(db))  # Aggregate
        .to_sink(AnalyticsSink())  # Analyze and print
    )

    # Execute
    print("\nExecuting advanced analytics pipeline...")
    env.execute()

    # Final database stats
    print("\n" + "=" * 60)
    print("Final Database Statistics")
    print("=" * 60)
    stats = db.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")


def example_service_based_analytics():
    """Service-based analytics example"""
    print("\n" + "=" * 60)
    print("Service-Based Analytics Example")
    print("=" * 60)

    # Create service
    service = SageTSDBService()

    # Generate and ingest data
    source = MultiSensorSource(num_sensors=2, points_per_sensor=20)
    data_points = source.generate()

    print("\nIngesting data...")
    for point in data_points:
        service.add(
            timestamp=point["timestamp"],
            value=point["value"],
            tags={
                "sensor_id": point["sensor_id"],
                "location": point["location"],
                "type": point["type"],
            },
        )

    # Perform window aggregation through service
    print("\nPerforming window aggregation...")
    start_time = data_points[0]["timestamp"]
    end_time = data_points[-1]["timestamp"]

    aggregated = service.window_aggregate(
        start_time=start_time,
        end_time=end_time,
        window_type="tumbling",
        window_size=10000,
        aggregation="avg",
        tags={"sensor_id": "sensor_00"},
    )

    print(f"\nAggregated Results: {len(aggregated)} windows")
    for i, result in enumerate(aggregated):
        print(f"Window {i+1}: value={result['value']:.2f}")

    # Service statistics
    print("\nService Statistics:")
    stats = service.stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SAGE TSDB Advanced Examples")
    print("=" * 60)

    try:
        # Run analytics DAG
        example_advanced_analytics_dag()

        print("\n" + "-" * 60 + "\n")

        # Run service-based example
        example_service_based_analytics()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback

        traceback.print_exc()
