"""
Stream Join Example for SageTSDB

This example demonstrates out-of-order stream join:
1. Creating two streams with out-of-order data
2. Configuring join parameters
3. Performing window-based join
4. Analyzing join results
"""

from datetime import datetime

import numpy as np

from sage.middleware.components.sage_tsdb import OutOfOrderStreamJoin
from sage.middleware.components.sage_tsdb.python.sage_tsdb import TimeSeriesData


def generate_stream_data(
    base_time: int, n_points: int, stream_id: str, disorder_prob: float = 0.3
) -> list:
    """Generate time series data with potential out-of-order arrivals"""
    data = []

    for i in range(n_points):
        # Add random delay to simulate out-of-order arrival
        if np.random.rand() < disorder_prob:
            # Out of order: earlier timestamp
            delay = -np.random.randint(1, 5) * 1000
        else:
            # In order
            delay = 0

        timestamp = base_time + i * 1000 + delay
        value = 100 + 10 * np.sin(i * 0.3) + np.random.randn() * 2
        tags = {"stream": stream_id, "type": "sensor"}

        data.append(TimeSeriesData(timestamp=timestamp, value=value, tags=tags))

    return data


def main():
    print("=" * 60)
    print("SageTSDB Out-of-Order Stream Join Example")
    print("=" * 60)

    # Generate two streams with out-of-order data
    base_time = int(datetime.now().timestamp() * 1000)

    print("\n1. Generating stream data...")
    left_stream = generate_stream_data(base_time, 20, "left", disorder_prob=0.3)
    right_stream = generate_stream_data(base_time + 500, 20, "right", disorder_prob=0.3)

    print(f"   Left stream: {len(left_stream)} points")
    print(f"   Right stream: {len(right_stream)} points")

    # Check for out-of-order data
    left_ooo = sum(
        1
        for i in range(1, len(left_stream))
        if left_stream[i].timestamp < left_stream[i - 1].timestamp
    )
    right_ooo = sum(
        1
        for i in range(1, len(right_stream))
        if right_stream[i].timestamp < right_stream[i - 1].timestamp
    )

    print(f"   Left stream out-of-order: {left_ooo} points")
    print(f"   Right stream out-of-order: {right_ooo} points")

    # Configure stream join
    print("\n2. Configuring stream join...")
    join_config = {
        "window_size": 5000,  # 5-second join window
        "max_delay": 3000,  # 3-second maximum delay
        "join_key": None,  # No equi-join, use window condition only
    }

    join_algo = OutOfOrderStreamJoin(join_config)
    print(f"   Window size: {join_config['window_size']}ms")
    print(f"   Max delay: {join_config['max_delay']}ms")

    # Perform join
    print("\n3. Performing stream join...")
    joined = join_algo.process(left_stream=left_stream, right_stream=right_stream)

    print(f"   Joined {len(joined)} pairs")

    # Display first few results
    print("\n4. Sample join results:")
    for i, (left, right) in enumerate(joined[:5]):
        time_diff = abs(left.timestamp - right.timestamp)
        print(f"\n   Pair {i + 1}:")
        print(f"     Left:  ts={left.timestamp}, value={left.value:.2f}")
        print(f"     Right: ts={right.timestamp}, value={right.value:.2f}")
        print(f"     Time difference: {time_diff}ms")

    # Join statistics
    print("\n5. Join statistics:")
    stats = join_algo.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Analyze time differences
    print("\n6. Time difference analysis:")
    time_diffs = [abs(left.timestamp - right.timestamp) for left, right in joined]
    if time_diffs:
        print(f"   Min: {min(time_diffs)}ms")
        print(f"   Max: {max(time_diffs)}ms")
        print(f"   Avg: {np.mean(time_diffs):.2f}ms")
        print(f"   Std: {np.std(time_diffs):.2f}ms")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
