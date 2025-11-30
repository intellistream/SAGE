"""
Stream Join Example with SAGE TSDB

This example demonstrates out-of-order stream join using SAGE TSDB:
1. Two data streams with potential out-of-order arrivals
2. Window-based join algorithms
3. Stream processing patterns
"""

import random
from datetime import datetime
from typing import Any

import numpy as np

from sage.middleware.components.sage_tsdb import SageTSDB, TimeRange


def generate_stream_data(
    stream_id: str,
    num_points: int = 50,
    disorder_probability: float = 0.3,
    max_delay_ms: int = 3000,
) -> list[dict[str, Any]]:
    """Generate time series stream with out-of-order data"""
    data_points = []
    base_time = int(datetime.now().timestamp() * 1000)

    for i in range(num_points):
        # Determine if this point should be out of order
        if random.random() < disorder_probability:
            # Add negative delay to simulate out-of-order arrival
            delay = -random.randint(100, max_delay_ms)
        else:
            # In-order or slightly delayed
            delay = random.randint(0, 500)

        timestamp = base_time + i * 1000 + delay
        value = 100 + 20 * np.sin(i * 0.2) + np.random.randn() * 5

        data_points.append(
            {
                "timestamp": timestamp,
                "value": value,
                "stream_id": stream_id,
                "sequence": i,
            }
        )

    return data_points


def join_streams(
    left_stream: list[dict[str, Any]],
    right_stream: list[dict[str, Any]],
    window_size: int = 5000,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Join two streams based on time windows"""
    joined_pairs = []

    # Sort both streams by timestamp
    left_sorted = sorted(left_stream, key=lambda x: x["timestamp"])
    right_sorted = sorted(right_stream, key=lambda x: x["timestamp"])

    # Simple window-based join
    for left_data in left_sorted:
        for right_data in right_sorted:
            time_diff = abs(left_data["timestamp"] - right_data["timestamp"])

            # If within window, create pair
            if time_diff <= window_size:
                joined_pairs.append((left_data, right_data))

    return joined_pairs


def example_stream_join_with_time_range():
    """Example: Basic stream join with time range"""
    print("\n" + "=" * 60)
    print("Stream Join with Time Range Example")
    print("=" * 60)

    # Generate two streams
    print("\nGenerating streams...")
    left_stream = generate_stream_data(stream_id="left", num_points=30, disorder_probability=0.3)
    right_stream = generate_stream_data(stream_id="right", num_points=30, disorder_probability=0.3)

    print(f"Left stream: {len(left_stream)} points")
    print(f"Right stream: {len(right_stream)} points")

    # Join streams
    print("\nPerforming join...")
    joined_pairs = join_streams(left_stream, right_stream, window_size=5000)

    print(f"\nJoined {len(joined_pairs)} pairs")

    # Show results
    print("\nJoin results (first 5 pairs):")
    for i, (left, right) in enumerate(joined_pairs[:5]):
        time_diff = abs(left["timestamp"] - right["timestamp"])
        print(f"\nPair {i + 1}:")
        print(f"  Left:  seq={left['sequence']}, ts={left['timestamp']}, value={left['value']:.2f}")
        print(
            f"  Right: seq={right['sequence']}, ts={right['timestamp']}, value={right['value']:.2f}"
        )
        print(f"  Time diff: {time_diff}ms")

    # Statistics
    if joined_pairs:
        time_diffs = [abs(left["timestamp"] - right["timestamp"]) for left, right in joined_pairs]
        print("\nJoin Statistics:")
        print(f"  Total pairs: {len(joined_pairs)}")
        print(f"  Avg time diff: {np.mean(time_diffs):.2f}ms")
        print(f"  Max time diff: {np.max(time_diffs):.2f}ms")
        print(f"  Min time diff: {np.min(time_diffs):.2f}ms")


def example_stream_ingestion_and_join():
    """Example: Ingest streams and query joins"""
    print("\n" + "=" * 60)
    print("Stream Ingestion and Join Example")
    print("=" * 60)

    # Create TSDB instances for left and right streams
    db_left = SageTSDB()
    db_right = SageTSDB()

    # Generate streams
    print("\nGenerating streams...")
    left_stream = generate_stream_data(stream_id="left", num_points=25, disorder_probability=0.2)
    right_stream = generate_stream_data(stream_id="right", num_points=25, disorder_probability=0.2)

    # Ingest into databases
    print("\nIngesting left stream...")
    for data in left_stream:
        db_left.add(timestamp=data["timestamp"], value=data["value"], tags={"stream": "left"})

    print("Ingesting right stream...")
    for data in right_stream:
        db_right.add(timestamp=data["timestamp"], value=data["value"], tags={"stream": "right"})

    print(f"Left DB size: {db_left.size}")
    print(f"Right DB size: {db_right.size}")

    # Query joined data
    print("\nQuerying joined data from time window...")
    base_time = min(data["timestamp"] for data in left_stream + right_stream)
    end_time = max(data["timestamp"] for data in left_stream + right_stream)

    time_range = TimeRange(start_time=base_time, end_time=end_time)

    left_results = db_left.query(time_range)
    right_results = db_right.query(time_range)

    print(f"Left query results: {len(left_results)} points")
    print(f"Right query results: {len(right_results)} points")

    # Manual join
    print("\nPerforming join on queried data...")
    joined = 0
    for left_result in left_results:
        for right_result in right_results:
            time_diff = abs(left_result.timestamp - right_result.timestamp)
            if time_diff <= 5000:  # 5 second window
                joined += 1

    print(f"Joined pairs within 5-second window: {joined}")

    # Database stats
    print("\nDatabase Statistics:")
    print("\nLeft Stream DB:")
    for key, value in db_left.get_stats().items():
        print(f"  {key}: {value}")

    print("\nRight Stream DB:")
    for key, value in db_right.get_stats().items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SAGE TSDB Stream Join Examples")
    print("=" * 60)

    try:
        # Run stream join with time range
        example_stream_join_with_time_range()

        print("\n" + "-" * 60 + "\n")

        # Run stream ingestion and join
        example_stream_ingestion_and_join()

        print("\n" + "=" * 60)
        print("Examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback

        traceback.print_exc()
