"""
Service Integration Example for SageTSDB

This example demonstrates using SageTSDB through the service interface:
1. Creating a service instance
2. Adding data through the service
3. Querying and aggregating data
4. Using stream join functionality
"""

from datetime import datetime

import numpy as np

from sage.middleware.components.sage_tsdb import SageTSDBService, SageTSDBServiceConfig


def main():
    print("=" * 60)
    print("SageTSDB Service Integration Example")
    print("=" * 60)

    # Create service
    print("\n1. Creating SageTSDB service...")
    config = SageTSDBServiceConfig(
        enable_compression=False,
        max_memory_mb=512,
        default_window_size=10000,  # 10 seconds
        default_aggregation="avg",
    )
    service = SageTSDBService(config=config)
    print("   Service created successfully")

    # Add data through service
    base_time = int(datetime.now().timestamp() * 1000)

    print("\n2. Adding data through service...")
    for i in range(30):
        timestamp = base_time + i * 1000
        value = 50 + 20 * np.sin(i * 0.2) + np.random.randn() * 3
        tags = {"device": "device_01", "metric": "cpu_usage"}
        fields = {"unit": "percent"}

        service.add(timestamp=timestamp, value=value, tags=tags, fields=fields)

    print("   Added 30 data points")

    # Query data
    print("\n3. Querying data through service...")
    results = service.query(
        start_time=base_time,
        end_time=base_time + 20000,  # First 20 seconds
        tags={"device": "device_01"},
        limit=10,
    )

    print(f"   Retrieved {len(results)} data points")
    print(f"   First result: {results[0]}")

    # Window aggregation through service
    print("\n4. Window aggregation...")
    aggregated = service.window_aggregate(
        start_time=base_time,
        end_time=base_time + 30000,
        window_type="tumbling",
        window_size=5000,  # 5-second windows
        aggregation="avg",
        tags={"device": "device_01"},
    )

    print(f"   Aggregated into {len(aggregated)} windows")
    for i, agg in enumerate(aggregated):
        print(f"   Window {i + 1}: value={agg['value']:.2f}")

    # Stream join through service
    print("\n5. Stream join example...")

    # Create two streams
    left_stream = []
    right_stream = []

    for i in range(15):
        left_stream.append(
            {
                "timestamp": base_time + i * 1000,
                "value": 100 + np.random.randn() * 5,
                "tags": {"stream": "left"},
            }
        )

        right_stream.append(
            {
                "timestamp": base_time + i * 1000 + 500,  # 0.5s offset
                "value": 200 + np.random.randn() * 5,
                "tags": {"stream": "right"},
            }
        )

    joined = service.stream_join(
        left_stream=left_stream,
        right_stream=right_stream,
        window_size=2000,  # 2-second window
        max_delay=1000,  # 1-second max delay
    )

    print(f"   Joined {len(joined)} pairs")
    if joined:
        print(f"   First pair: {joined[0]}")

    # Service statistics
    print("\n6. Service statistics:")
    stats = service.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
