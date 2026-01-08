"""
Basic SAGE TSDB Example

This example demonstrates:
1. Creating a time series database
2. Ingesting streaming data
3. Querying and aggregating time series data
"""

from datetime import datetime
from typing import Any

import numpy as np

from sage.middleware.components.sage_tsdb import SageTSDB, TimeRange


def generate_time_series_data(
    num_points: int = 100, sensor_id: str = "sensor_01"
) -> list[dict[str, Any]]:
    """Generate simulated time series data"""
    data_points = []
    base_time = int(datetime.now().timestamp() * 1000)

    for i in range(num_points):
        timestamp = base_time + i * 1000  # 1 second intervals
        value = 20 + 5 * np.sin(i * 0.1) + np.random.randn()

        data_points.append(
            {
                "timestamp": timestamp,
                "value": value,
                "tags": {
                    "sensor_id": sensor_id,
                    "location": "room_a",
                    "unit": "celsius",
                },
            }
        )

    return data_points


def example_basic_ingestion_and_query():
    """Example: Basic TSDB ingestion and query"""
    print("\n" + "=" * 60)
    print("Example 1: Basic Ingestion and Query")
    print("=" * 60)

    # Create TSDB instance
    db = SageTSDB()

    # Generate and ingest data
    data_points = generate_time_series_data(num_points=50, sensor_id="temp_sensor")
    print(f"\nIngesting {len(data_points)} data points...")

    for point in data_points:
        db.add(
            timestamp=point["timestamp"],
            value=point["value"],
            tags=point["tags"],
        )

    print(f"Ingested {db.size} points into database")

    # Query data
    print("\nQuerying data...")
    if data_points:
        start_time = data_points[0]["timestamp"]
        end_time = data_points[-1]["timestamp"]

        time_range = TimeRange(start_time=start_time, end_time=end_time)
        results = db.query(time_range)

        print(f"Query returned {len(results)} points")
        print("\nFirst 5 results:")
        for i, result in enumerate(results[:5]):
            print(f"  {i + 1}. timestamp={result.timestamp}, value={result.value:.2f}")


def example_window_aggregation():
    """Example: Window-based aggregation"""
    print("\n" + "=" * 60)
    print("Example 2: Window Aggregation")
    print("=" * 60)

    # Create TSDB instance
    db = SageTSDB()

    # Generate and ingest data
    data_points = generate_time_series_data(num_points=30, sensor_id="humidity_sensor")
    print(f"\nIngesting {len(data_points)} data points for aggregation...")

    for point in data_points:
        db.add(
            timestamp=point["timestamp"],
            value=point["value"],
            tags=point["tags"],
        )

    # Query with windowing
    if data_points:
        start_time = data_points[0]["timestamp"]
        end_time = data_points[-1]["timestamp"]

        print(f"\nQuerying with time range: {start_time} to {end_time}")
        time_range = TimeRange(start_time=start_time, end_time=end_time)
        results = db.query(time_range)

        # Calculate statistics
        if results:
            values: np.ndarray = np.array([r.value for r in results])
            print(f"\nStatistics from {len(values)} points:")
            print(f"  Mean: {np.mean(values):.2f}")
            print(f"  Std Dev: {np.std(values):.2f}")
            print(f"  Min: {np.min(values):.2f}")
            print(f"  Max: {np.max(values):.2f}")


def example_multi_sensor():
    """Example: Multi-sensor data"""
    print("\n" + "=" * 60)
    print("Example 3: Multi-Sensor Data")
    print("=" * 60)

    # Create TSDB instance
    db = SageTSDB()

    # Generate data from multiple sensors
    sensors = ["temp_sensor", "humidity_sensor", "pressure_sensor"]
    print(f"\nIngesting data from {len(sensors)} sensors...")

    base_time = int(datetime.now().timestamp() * 1000)
    total_points = 0

    for sensor_id in sensors:
        data_points = generate_time_series_data(num_points=20, sensor_id=sensor_id)
        for point in data_points:
            db.add(
                timestamp=point["timestamp"],
                value=point["value"],
                tags=point["tags"],
            )
            total_points += 1

    print(f"Ingested {total_points} points from {len(sensors)} sensors")
    # Print final database size
    print(f"Database size: {db.size}")

    # Query data by sensor
    print("\nQuerying data by sensor:")
    for sensor_id in sensors:
        start_time = base_time
        end_time = base_time + 30000
        time_range = TimeRange(start_time=start_time, end_time=end_time)

        # Note: Query with tags may need adjustment based on actual API
        results = db.query(time_range)
        print(f"  {sensor_id}: {len(results)} points")


def example_database_statistics():
    """Example: Database statistics"""
    print("\n" + "=" * 60)
    print("Example 4: Database Statistics")
    print("=" * 60)

    # Create TSDB instance
    db = SageTSDB()

    # Ingest data
    data_points = generate_time_series_data(num_points=100, sensor_id="stat_sensor")
    print(f"\nIngesting {len(data_points)} data points...")

    for point in data_points:
        db.add(
            timestamp=point["timestamp"],
            value=point["value"],
            tags=point["tags"],
        )

    # Get statistics
    print("\nDatabase Statistics:")
    stats = db.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print(f"\nTotal points in database: {db.size}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SAGE TSDB Basic Examples")
    print("=" * 60)

    try:
        # Run examples
        example_basic_ingestion_and_query()
        example_window_aggregation()
        example_multi_sensor()
        example_database_statistics()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback

        traceback.print_exc()
