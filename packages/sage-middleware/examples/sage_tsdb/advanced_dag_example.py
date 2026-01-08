"""
Advanced SAGE TSDB Example

This example demonstrates advanced features:
1. Multi-sensor data ingestion
2. Complex window aggregations
3. Real-time anomaly detection
4. Integration with SAGE service layer
"""

from datetime import datetime
from typing import Any

import numpy as np

from sage.middleware.components.sage_tsdb import SageTSDB, TimeRange


def generate_multi_sensor_data(
    num_sensors: int = 3, points_per_sensor: int = 30
) -> list[dict[str, Any]]:
    """Generate data from multiple sensors"""
    data_points = []
    base_time = int(datetime.now().timestamp() * 1000)

    for sensor_id in range(num_sensors):
        for i in range(points_per_sensor):
            timestamp = base_time + i * 1000
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


def detect_anomalies(
    db: SageTSDB, data_points: list[dict[str, Any]], threshold_std: float = 2.5
) -> list[dict[str, Any]]:
    """Detect anomalies in time series data"""
    results = []

    for data in data_points:
        # Query historical data
        time_range = TimeRange(
            start_time=data["timestamp"] - 30000,  # Last 30 seconds
            end_time=data["timestamp"],
        )

        historical = db.query(time_range=time_range)

        is_anomaly = False
        anomaly_score = 0.0

        if len(historical) > 5:  # Need enough data
            values: np.ndarray = np.array([h.value for h in historical])
            mean = np.mean(values)
            std = np.std(values)

            if std > 0:
                z_score = abs((data["value"] - mean) / std)
                is_anomaly = z_score > threshold_std
                anomaly_score = z_score

        results.append(
            {
                **data,
                "is_anomaly": is_anomaly,
                "anomaly_score": anomaly_score,
                "historical_count": len(historical),
            }
        )

    return results


def compute_window_statistics(
    db: SageTSDB, data_points: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Compute window-based statistics"""
    results = []

    for i, data in enumerate(data_points):
        # Every 10 points, compute aggregations
        if (i + 1) % 10 == 0:
            # Query recent data
            time_range = TimeRange(start_time=data["timestamp"] - 30000, end_time=data["timestamp"])

            recent_data = db.query(time_range=time_range)

            # Compute statistics
            if recent_data:
                values: np.ndarray = np.array([r.value for r in recent_data])
                aggregations = {
                    "count": len(values),
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "min": np.min(values),
                    "max": np.max(values),
                }
            else:
                aggregations = {"count": 0}

            results.append(
                {
                    **data,
                    "aggregations": aggregations,
                    "has_aggregation": True,
                }
            )
        else:
            results.append({**data, "has_aggregation": False})

    return results


def example_advanced_analytics():
    """Advanced analytics with anomaly detection"""
    print("\n" + "=" * 60)
    print("Advanced Analytics Example")
    print("=" * 60)

    # Create TSDB instance
    db = SageTSDB()

    # Generate and ingest multi-sensor data
    data_points = generate_multi_sensor_data(num_sensors=3, points_per_sensor=40)
    print(f"\nIngesting {len(data_points)} multi-sensor data points...")

    for point in data_points:
        db.add(
            timestamp=point["timestamp"],
            value=point["value"],
            tags={
                "sensor_id": point["sensor_id"],
                "location": point["location"],
                "type": point["type"],
            },
        )

    # Detect anomalies
    print("\nDetecting anomalies...")
    anomaly_results = detect_anomalies(db, data_points, threshold_std=2.0)

    # Count and display anomalies
    anomalies = [r for r in anomaly_results if r["is_anomaly"]]
    print(f"Found {len(anomalies)} anomalies out of {len(data_points)} points")

    if anomalies:
        print("\nAnomalies detected:")
        for anomaly in anomalies[:5]:  # Show first 5
            print(
                f"  Sensor: {anomaly['sensor_id']}, Value: {anomaly['value']:.2f}, Score: {anomaly['anomaly_score']:.2f}"
            )

    # Compute window statistics
    print("\nComputing window statistics...")
    window_results = compute_window_statistics(db, data_points)

    aggregation_count = sum(1 for r in window_results if r["has_aggregation"])
    print(f"Computed {aggregation_count} window aggregations")

    # Show sample aggregations
    for result in window_results:
        if result["has_aggregation"]:
            agg = result["aggregations"]
            print(f"\nAggregation for {result['sensor_id']}:")
            print(f"  Count: {agg['count']}")
            print(f"  Mean: {agg['mean']:.2f}")
            print(f"  Min: {agg['min']:.2f}")
            print(f"  Max: {agg['max']:.2f}")
            break


def example_multi_sensor_comparison():
    """Compare data from multiple sensors"""
    print("\n" + "=" * 60)
    print("Multi-Sensor Comparison Example")
    print("=" * 60)

    # Create separate TSDB for each sensor
    sensors_db = {
        "sensor_00": SageTSDB(),
        "sensor_01": SageTSDB(),
        "sensor_02": SageTSDB(),
    }

    # Generate and ingest data
    data_points = generate_multi_sensor_data(num_sensors=3, points_per_sensor=25)
    print("\nIngesting data from 3 sensors...")

    for point in data_points:
        sensor_id = point["sensor_id"]
        if sensor_id in sensors_db:
            sensors_db[sensor_id].add(
                timestamp=point["timestamp"],
                value=point["value"],
                tags={
                    "location": point["location"],
                    "type": point["type"],
                },
            )

    # Compare sensor statistics
    print("\nSensor Comparison:")
    print(f"{'Sensor':<15} {'Points':<10} {'Mean':<10} {'Std':<10}")
    print("-" * 45)

    for sensor_id, db in sensors_db.items():
        time_range = TimeRange(
            start_time=0, end_time=int(datetime.now().timestamp() * 1000) + 100000
        )
        results = db.query(time_range)

        if results:
            values: np.ndarray = np.array([r.value for r in results])
            mean = np.mean(values)
            std = np.std(values)
            print(f"{sensor_id:<15} {len(results):<10} {mean:<10.2f} {std:<10.2f}")

    # Database statistics
    print("\nDatabase Statistics:")
    for sensor_id, db in sensors_db.items():
        stats = db.get_stats()
        print(f"\n{sensor_id}:")
        for key, value in stats.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SAGE TSDB Advanced Examples")
    print("=" * 60)

    try:
        # Run advanced analytics
        example_advanced_analytics()

        print("\n" + "-" * 60 + "\n")

        # Run multi-sensor comparison
        example_multi_sensor_comparison()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback

        traceback.print_exc()
