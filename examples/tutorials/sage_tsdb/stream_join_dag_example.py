"""
Stream Join Example with SAGE TSDB

This example demonstrates out-of-order stream join using SAGE TSDB:
1. Two data streams with potential out-of-order arrivals
2. Window-based join with watermarking
3. Integration with SAGE DAG workflow
"""

import random
from datetime import datetime
from typing import Any, Dict, List

import numpy as np

from sage.middleware.components.sage_tsdb import OutOfOrderStreamJoin
from sage.middleware.components.sage_tsdb.python.sage_tsdb import TimeSeriesData
from sage.libs.rag.local_env import LocalEnvironment
from sage.libs.rag.node import MapFunction, SinkFunction, SourceFunction


class OutOfOrderStreamSource(SourceFunction):
    """Generate time series stream with out-of-order data"""

    def __init__(
        self,
        stream_id: str,
        num_points: int = 50,
        disorder_probability: float = 0.3,
        max_delay_ms: int = 3000,
    ):
        super().__init__()
        self.stream_id = stream_id
        self.num_points = num_points
        self.disorder_probability = disorder_probability
        self.max_delay_ms = max_delay_ms
        self.base_time = int(datetime.now().timestamp() * 1000)

    def generate(self) -> List[Dict[str, Any]]:
        """Generate data points with potential out-of-order arrivals"""
        data_points = []

        for i in range(self.num_points):
            # Determine if this point should be out of order
            if random.random() < self.disorder_probability:
                # Add negative delay to simulate out-of-order arrival
                delay = -random.randint(100, self.max_delay_ms)
            else:
                # In-order or slightly delayed
                delay = random.randint(0, 500)

            timestamp = self.base_time + i * 1000 + delay
            value = 100 + 20 * np.sin(i * 0.2) + np.random.randn() * 5

            data_points.append(
                {
                    "timestamp": timestamp,
                    "value": value,
                    "stream_id": self.stream_id,
                    "sequence": i,
                }
            )

        return data_points


class StreamJoinNode(MapFunction):
    """Join two streams using out-of-order stream join algorithm"""

    def __init__(
        self, window_size: int = 5000, max_delay: int = 3000, join_key: str = None
    ):
        super().__init__()
        self.join_algo = OutOfOrderStreamJoin(
            {"window_size": window_size, "max_delay": max_delay, "join_key": join_key}
        )
        self.left_buffer = []
        self.right_buffer = []

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Buffer data and perform join when both streams have data"""
        # Convert to TimeSeriesData
        ts_data = TimeSeriesData(
            timestamp=data["timestamp"],
            value=data["value"],
            tags={"stream_id": data["stream_id"]},
        )

        # Route to appropriate buffer
        if data["stream_id"] == "left":
            self.left_buffer.append(ts_data)
        else:
            self.right_buffer.append(ts_data)

        # Perform join if both buffers have data
        joined_pairs = []
        if self.left_buffer and self.right_buffer:
            # Process batch
            batch_size = min(10, len(self.left_buffer), len(self.right_buffer))
            left_batch = self.left_buffer[:batch_size]
            right_batch = self.right_buffer[:batch_size]

            # Join
            pairs = self.join_algo.process(
                left_stream=left_batch, right_stream=right_batch
            )

            # Remove processed data
            self.left_buffer = self.left_buffer[batch_size:]
            self.right_buffer = self.right_buffer[batch_size:]

            # Format results
            for left, right in pairs:
                joined_pairs.append(
                    {
                        "left_timestamp": left.timestamp,
                        "left_value": left.value,
                        "right_timestamp": right.timestamp,
                        "right_value": right.value,
                        "time_diff": abs(left.timestamp - right.timestamp),
                    }
                )

        return {
            "joined_pairs": joined_pairs,
            "left_buffer_size": len(self.left_buffer),
            "right_buffer_size": len(self.right_buffer),
            "join_stats": self.join_algo.get_stats(),
        }


class JoinResultSink(SinkFunction):
    """Print join results"""

    def __init__(self):
        super().__init__()
        self.total_pairs = 0

    def execute(self, data: Dict[str, Any]) -> None:
        """Print join results"""
        pairs = data.get("joined_pairs", [])

        if pairs:
            self.total_pairs += len(pairs)
            print(f"\n{'=' * 60}")
            print(f"Joined {len(pairs)} pairs (Total: {self.total_pairs})")
            print(f"{'=' * 60}")

            # Show first few pairs
            for i, pair in enumerate(pairs[:3]):
                print(f"\nPair {i+1}:")
                print(f"  Left:  ts={pair['left_timestamp']}, value={pair['left_value']:.2f}")
                print(
                    f"  Right: ts={pair['right_timestamp']}, value={pair['right_value']:.2f}"
                )
                print(f"  Time diff: {pair['time_diff']}ms")

            # Show statistics
            if data.get("join_stats"):
                print(f"\nJoin Statistics:")
                for key, value in data["join_stats"].items():
                    print(f"  {key}: {value}")


class DataRouter(MapFunction):
    """Route data to left or right stream"""

    def __init__(self):
        super().__init__()

    def execute(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Route data points"""
        return data


def example_stream_join_dag():
    """Example: Stream join with DAG"""
    print("\n" + "=" * 60)
    print("Stream Join DAG Example")
    print("=" * 60)

    # Create environment
    env = LocalEnvironment()

    # Create two streams
    left_source = OutOfOrderStreamSource(
        stream_id="left", num_points=30, disorder_probability=0.3
    )
    right_source = OutOfOrderStreamSource(
        stream_id="right", num_points=30, disorder_probability=0.3
    )

    # Create join node
    join_node = StreamJoinNode(window_size=5000, max_delay=3000)

    # Build pipeline for left stream
    left_pipeline = (
        env.from_source(left_source)
        .flat_map(lambda data_list: data_list)
        .map(join_node)
    )

    # Build pipeline for right stream
    right_pipeline = (
        env.from_source(right_source)
        .flat_map(lambda data_list: data_list)
        .map(join_node)
    )

    # Merge and sink
    left_pipeline.to_sink(JoinResultSink())
    right_pipeline.to_sink(JoinResultSink())

    # Execute
    print("\nExecuting stream join pipeline...")
    env.execute()

    print("\n" + "=" * 60)
    print("Stream join completed!")
    print("=" * 60)


def example_simple_join():
    """Simplified join example"""
    print("\n" + "=" * 60)
    print("Simple Stream Join Example")
    print("=" * 60)

    # Create join algorithm
    join_algo = OutOfOrderStreamJoin({"window_size": 5000, "max_delay": 2000})

    # Generate two streams
    base_time = int(datetime.now().timestamp() * 1000)

    left_stream = []
    right_stream = []

    for i in range(20):
        # Left stream
        left_stream.append(
            TimeSeriesData(
                timestamp=base_time + i * 1000 + random.randint(-500, 500),
                value=100 + random.random() * 10,
                tags={"stream": "left"},
            )
        )

        # Right stream (slightly offset)
        right_stream.append(
            TimeSeriesData(
                timestamp=base_time + i * 1000 + 500 + random.randint(-500, 500),
                value=200 + random.random() * 10,
                tags={"stream": "right"},
            )
        )

    # Perform join
    print("\nPerforming join...")
    joined = join_algo.process(left_stream=left_stream, right_stream=right_stream)

    print(f"\nJoined {len(joined)} pairs")

    # Show results
    for i, (left, right) in enumerate(joined[:5]):
        print(f"\nPair {i+1}:")
        print(f"  Left:  ts={left.timestamp}, value={left.value:.2f}")
        print(f"  Right: ts={right.timestamp}, value={right.value:.2f}")
        print(f"  Time diff: {abs(left.timestamp - right.timestamp)}ms")

    # Statistics
    print("\nJoin Statistics:")
    stats = join_algo.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SAGE TSDB Stream Join Examples")
    print("=" * 60)

    try:
        # Run simple example first
        example_simple_join()

        print("\n" + "-" * 60 + "\n")

        # Run DAG example
        # example_stream_join_dag()

        print("\n" + "=" * 60)
        print("Examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback

        traceback.print_exc()
