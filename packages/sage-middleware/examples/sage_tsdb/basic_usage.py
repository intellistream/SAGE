"""
Basic usage example for SageTSDB

This example demonstrates:
1. Creating a time series database
2. Adding data points
3. Querying with time ranges and tags
4. Window-based aggregations
"""

from datetime import datetime

import numpy as np

from sage.middleware.components.sage_tsdb import SageTSDB, TimeRange


def main():
    print("=" * 60)
    print("SageTSDB Basic Usage Example")
    print("=" * 60)

    # Create database
    print("\n1. Creating time series database...")
    db = SageTSDB()

    # Generate sample data
    print("\n2. Adding time series data...")
    base_time = int(datetime.now().timestamp() * 1000)

    # Add individual data points
    for i in range(10):
        timestamp = base_time + i * 1000  # 1 second intervals
        value = 20 + 5 * np.sin(i * 0.5) + np.random.randn()
        tags = {"sensor": "temp_01", "location": "room_a"}
        fields = {"unit": "celsius"}

        db.add(timestamp=timestamp, value=value, tags=tags, fields=fields)

    print(f"   Added {db.size} data points")

    # Add batch data
    print("\n3. Adding batch data...")
    timestamps = [base_time + (i + 10) * 1000 for i in range(20)]
    values = [20 + 5 * np.sin(i * 0.5) + np.random.randn() for i in range(10, 30)]
    tags_list = [{"sensor": "temp_01", "location": "room_a"} for _ in range(20)]

    db.add_batch(timestamps=timestamps, values=values, tags_list=tags_list)
    print(f"   Total data points: {db.size}")

    # Query data
    print("\n4. Querying time series data...")
    time_range = TimeRange(
        start_time=base_time,
        end_time=base_time + 15000,  # First 15 seconds
    )

    results = db.query(time_range=time_range, tags={"sensor": "temp_01"})
    print(f"   Found {len(results)} data points in time range")
    print(f"   First result: timestamp={results[0].timestamp}, value={results[0].value:.2f}")
    print(f"   Last result: timestamp={results[-1].timestamp}, value={results[-1].value:.2f}")

    # Window aggregation
    print("\n5. Window-based aggregation...")
    aggregated = db.query(
        time_range=TimeRange(start_time=base_time, end_time=base_time + 30000),
        tags={"sensor": "temp_01"},
        aggregation="avg",
        window_size=5000,  # 5-second windows
    )

    print(f"   Aggregated into {len(aggregated)} windows")
    for i, agg in enumerate(aggregated):
        print(f"   Window {i + 1}: timestamp={agg.timestamp}, avg_value={agg.value:.2f}")

    # Database statistics
    print("\n6. Database statistics:")
    stats = db.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
