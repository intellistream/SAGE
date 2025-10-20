"""
Basic SAGE TSDB Example with DAG Integration

This example demonstrates:
1. Creating a time series database
2. Ingesting streaming data through SAGE pipeline
3. Querying and aggregating time series data
4. Integrating with SAGE DAG workflow
"""

import time
from datetime import datetime
from typing import Any, Dict, List

import numpy as np

from sage.middleware.components.sage_tsdb import SageTSDB, SageTSDBService, TimeRange
from sage.libs.rag.local_env import LocalEnvironment
from sage.libs.rag.node import MapFunction, SinkFunction, SourceFunction


class TimeSeriesDataSource(SourceFunction):
    """Generate simulated time series data"""

    def __init__(self, num_points: int = 100, sensor_id: str = "sensor_01"):
        super().__init__()
        self.num_points = num_points
        self.sensor_id = sensor_id
        self.base_time = int(datetime.now().timestamp() * 1000)

    def generate(self) -> List[Dict[str, Any]]:
        """Generate time series data points"""
        data_points = []

        for i in range(self.num_points):
            timestamp = self.base_time + i * 1000  # 1 second intervals
            value = 20 + 5 * np.sin(i * 0.1) + np.random.randn()

            data_points.append(
                {
                    "timestamp": timestamp,
                    "value": value,
                    "tags": {
                        "sensor_id": self.sensor_id,
                        "location": "room_a",
                        "unit": "celsius",
                    },
                }
            )

        return data_points


class TSDBIngestNode(MapFunction):
    """Ingest data into SAGE TSDB"""

    def __init__(self, db: SageTSDB):
        super().__init__()
        self.db = db

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest a single data point"""
        idx = self.db.add(
            timestamp=data["timestamp"],
            value=data["value"],
            tags=data["tags"],
        )

        return {
            "index": idx,
            "timestamp": data["timestamp"],
            "value": data["value"],
            "status": "ingested",
        }


class TSDBQueryNode(MapFunction):
    """Query time series data from SAGE TSDB"""

    def __init__(self, db: SageTSDB, window_size: int = 10000):
        super().__init__()
        self.db = db
        self.window_size = window_size

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Query recent data and compute statistics"""
        current_time = data["timestamp"]

        # Query recent data
        time_range = TimeRange(
            start_time=current_time - self.window_size, end_time=current_time
        )

        results = self.db.query(
            time_range=time_range, tags={"sensor_id": data["tags"]["sensor_id"]}
        )

        # Compute statistics
        if results:
            values = [r.value for r in results]
            stats = {
                "count": len(values),
                "mean": np.mean(values),
                "std": np.std(values),
                "min": np.min(values),
                "max": np.max(values),
            }
        else:
            stats = {"count": 0}

        return {
            "timestamp": current_time,
            "window_stats": stats,
            "data_point": data,
        }


class TSDBWindowAggregateNode(MapFunction):
    """Perform window-based aggregation"""

    def __init__(self, db: SageTSDB, aggregation: str = "avg"):
        super().__init__()
        self.db = db
        self.aggregation = aggregation
        self.start_time = None

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate data in windows"""
        if self.start_time is None:
            self.start_time = data["timestamp"] - 30000  # Start 30 seconds ago

        # Query and aggregate
        time_range = TimeRange(start_time=self.start_time, end_time=data["timestamp"])

        aggregated = self.db.query(
            time_range=time_range,
            tags={"sensor_id": data["tags"]["sensor_id"]},
            aggregation=self.aggregation,
            window_size=5000,  # 5-second windows
        )

        return {
            "timestamp": data["timestamp"],
            "aggregated_windows": len(aggregated),
            "aggregation_type": self.aggregation,
            "last_aggregated_value": aggregated[-1].value if aggregated else None,
        }


class ResultPrinterSink(SinkFunction):
    """Print results to console"""

    def __init__(self, print_every: int = 10):
        super().__init__()
        self.print_every = print_every
        self.count = 0

    def execute(self, data: Dict[str, Any]) -> None:
        """Print results periodically"""
        self.count += 1

        if self.count % self.print_every == 0:
            print(f"\n{'=' * 60}")
            print(f"Result #{self.count}")
            print(f"{'=' * 60}")

            if "window_stats" in data:
                print(f"Timestamp: {data['timestamp']}")
                print(f"Window Statistics:")
                for key, value in data["window_stats"].items():
                    if isinstance(value, float):
                        print(f"  {key}: {value:.2f}")
                    else:
                        print(f"  {key}: {value}")

            if "aggregated_windows" in data:
                print(f"Aggregated Windows: {data['aggregated_windows']}")
                print(f"Aggregation Type: {data['aggregation_type']}")
                if data["last_aggregated_value"] is not None:
                    print(f"Last Aggregated Value: {data['last_aggregated_value']:.2f}")


def example_basic_pipeline():
    """Example: Basic TSDB pipeline with ingestion and query"""
    print("\n" + "=" * 60)
    print("Example 1: Basic Time Series Pipeline")
    print("=" * 60)

    # Create TSDB instance
    db = SageTSDB()

    # Create environment
    env = LocalEnvironment()

    # Build pipeline
    (
        env.from_source(TimeSeriesDataSource(num_points=50, sensor_id="temp_sensor"))
        .flat_map(lambda data_list: data_list)  # Flatten list
        .map(TSDBIngestNode(db))
        .map(TSDBQueryNode(db, window_size=10000))
        .to_sink(ResultPrinterSink(print_every=5))
    )

    # Execute
    print("\nExecuting pipeline...")
    env.execute()

    # Print final database stats
    print("\n" + "=" * 60)
    print("Database Statistics:")
    print("=" * 60)
    stats = db.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")


def example_window_aggregation():
    """Example: Window-based aggregation"""
    print("\n" + "=" * 60)
    print("Example 2: Window Aggregation Pipeline")
    print("=" * 60)

    # Create TSDB instance
    db = SageTSDB()

    # Create environment
    env = LocalEnvironment()

    # Build pipeline with aggregation
    (
        env.from_source(TimeSeriesDataSource(num_points=30, sensor_id="humidity_sensor"))
        .flat_map(lambda data_list: data_list)
        .map(TSDBIngestNode(db))
        .map(TSDBWindowAggregateNode(db, aggregation="avg"))
        .to_sink(ResultPrinterSink(print_every=5))
    )

    # Execute
    print("\nExecuting pipeline with window aggregation...")
    env.execute()


def example_service_integration():
    """Example: Using TSDB through service interface"""
    print("\n" + "=" * 60)
    print("Example 3: Service Integration")
    print("=" * 60)

    # Create TSDB service
    service = SageTSDBService()

    # Generate data
    source = TimeSeriesDataSource(num_points=20, sensor_id="pressure_sensor")
    data_points = source.generate()

    # Ingest through service
    print("\nIngesting data through service...")
    for point in data_points:
        service.add(
            timestamp=point["timestamp"], value=point["value"], tags=point["tags"]
        )

    # Query through service
    print("\nQuerying data through service...")
    start_time = data_points[0]["timestamp"]
    end_time = data_points[-1]["timestamp"]

    results = service.query(
        start_time=start_time,
        end_time=end_time,
        tags={"sensor_id": "pressure_sensor"},
        aggregation="avg",
        window_size=5000,
    )

    print(f"\nQuery Results: {len(results)} aggregated windows")
    for i, result in enumerate(results[:5]):  # Show first 5
        print(f"Window {i+1}: value={result['value']:.2f}")

    # Service statistics
    print("\nService Statistics:")
    stats = service.stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SAGE TSDB DAG Integration Examples")
    print("=" * 60)

    try:
        # Run examples
        example_basic_pipeline()
        print("\n" + "-" * 60 + "\n")

        example_window_aggregation()
        print("\n" + "-" * 60 + "\n")

        example_service_integration()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback

        traceback.print_exc()
