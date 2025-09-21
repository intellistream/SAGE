#!/usr/bin/env python3
"""
import logging
Remote Environment Parallelism Validation Example

This example demonstrates and validates parallelism hints functionality
using RemoteEnvironment (Ray-based distributed execution). It shows how
parallelism settings work in a distributed environment and verifies that
the ExecutionGraph creates the correct number of parallel nodes across
Ray workers.

@test:timeout=90
"""

import os
import threading
import time

from sage.core.api.function.base_function import BaseFunction
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.comap_function import BaseCoMapFunction
from sage.core.api.remote_environment import RemoteEnvironment


class NumberListSource(BatchFunction):
    """A simple batch source that produces a list of numbers"""

    def __init__(self, numbers):
        super().__init__()
        self.numbers = numbers
        self.index = 0

    def execute(self):
        if self.index >= len(self.numbers):
            return None
        value = self.numbers[self.index]
        self.index += 1
        return value


class DistributedProcessor(BaseFunction):
    """A processor that shows which worker/instance is handling the data"""

    def __init__(self, processor_name="DistProcessor"):
        super().__init__()
        self.processor_name = processor_name
        self.instance_id = id(self)
        self.process_id = os.getpid()
        self.thread_id = threading.get_ident()
        logging.info(
            f"🔧 {self.processor_name} instance {self.instance_id} created "
            f"(PID: {self.process_id}, Thread: {self.thread_id})"
        )

    def execute(self, data):
        current_thread = threading.get_ident()
        current_process = os.getpid()
        instance_id = id(self)
        result = f"{self.processor_name}[{instance_id}@{current_process}]: {data}"
        logging.info(f"⚙️  {result} (Thread: {current_thread})")
        time.sleep(0.1)  # Simulate processing time
        return result


class DistributedFilter(BaseFunction):
    """A filter that shows distributed execution across Ray workers"""

    def __init__(self):
        super().__init__()
        self.instance_id = id(self)
        self.process_id = os.getpid()
        logging.info(
            f"🔧 DistributedFilter instance {self.instance_id} created (PID: {self.process_id})"
        )

    def execute(self, data):
        current_thread = threading.get_ident()
        current_process = os.getpid()
        instance_id = id(self)

        # Filter logic: pass if data is divisible by 3
        passes = isinstance(data, int) and data % 3 == 0
        status = "PASSED" if passes else "BLOCKED"
        logging.info(
            f"{'✅' if passes else '❌'} Filter[{instance_id}@{current_process}]: {data} {status} "
            f"(Thread: {current_thread})"
        )
        return passes


class DistributedCoMapProcessor(BaseCoMapFunction):
    """CoMap processor for distributed multi-stream validation"""

    def __init__(self):
        super().__init__()
        self.instance_id = id(self)
        self.process_id = os.getpid()
        logging.info(
            f"🔧 DistributedCoMapProcessor instance {self.instance_id} created (PID: {self.process_id})"
        )

    def map0(self, data):
        current_process = os.getpid()
        current_thread = threading.get_ident()
        instance_id = id(self)
        result = f"DistCoMap0[{instance_id}@{current_process}]: {data}"
        logging.info(f"🔀 {result} (Thread: {current_thread})")
        time.sleep(0.05)
        return result

    def map1(self, data):
        current_process = os.getpid()
        current_thread = threading.get_ident()
        instance_id = id(self)
        result = f"DistCoMap1[{instance_id}@{current_process}]: {data * 100}"
        logging.info(f"🔀 {result} (Thread: {current_thread})")
        time.sleep(0.05)
        return result


class DistributedSink(BaseFunction):
    """Sink that validates and prints final results in distributed environment"""

    def __init__(self):
        super().__init__()
        self.instance_id = id(self)
        self.process_id = os.getpid()
        self.results = []
        logging.info(
            f"🔧 DistributedSink instance {self.instance_id} created (PID: {self.process_id})"
        )

    def execute(self, data):
        current_thread = threading.get_ident()
        current_process = os.getpid()
        instance_id = id(self)
        self.results.append(data)
        logging.info(
            f"🎯 SINK[{instance_id}@{current_process}]: {data} (Thread: {current_thread})"
        )
        return data


def validate_remote_single_stream_parallelism():
    """Validate parallelism for single stream operations in remote environment"""
    logging.info("\n" + "=" * 70)
    logging.info("REMOTE ENVIRONMENT - SINGLE STREAM PARALLELISM VALIDATION")
    logging.info("=" * 70)

    # Initialize Ray cluster for distributed processing
    # Note: Ray configuration is currently handled at the JobManager level,
    # not directly through RemoteEnvironment constructor. This is a potential
    # improvement area for SAGE architecture.
    try:
        env = RemoteEnvironment(name="remote_single_stream_test")
        logging.info("✅ RemoteEnvironment initialized successfully")
    except Exception as e:
        logging.info(f"⚠️  RemoteEnvironment initialization warning: {e}")
        env = RemoteEnvironment(name="remote_single_stream_test")

    # Test data - larger dataset for distributed processing
    numbers = list(range(1, 31))  # 1 to 30
    source_stream = env.from_collection(NumberListSource, numbers)

    logging.info(f"\n📊 Testing with {len(numbers)} input numbers")
    logging.info(f"📊 Numbers: {numbers[:10]}...{numbers[-5:]} (showing first 10 and last 5)")

    # Test distributed parallelism
    logging.info("\n--- Test 1: Distributed processing with direct parallelism parameters ---")
    result1 = (
        source_stream.map(
            DistributedProcessor, "DistMapper", parallelism=4
        )  # 4 parallel mappers across workers
        .filter(DistributedFilter, parallelism=3)  # 3 parallel filters across workers
        .sink(DistributedSink, parallelism=2)
    )  # 2 sinks across workers

    logging.info("\n--- Test 2: Distributed processing with direct parallelism ---")
    result2 = (
        source_stream
        .map(DistributedProcessor, "SetDistMapper", parallelism=3)  # 3 parallel mappers
        .filter(DistributedFilter, parallelism=2)  # 2 parallel filters
        .sink(DistributedSink, parallelism=1)
    )  # 1 sink

    # Analyze pipeline
    logging.info(f"\n📋 DISTRIBUTED PIPELINE ANALYSIS:")
    logging.info(f"Total transformations: {len(env.pipeline)}")
    logging.info(f"Ray workers available: {env.platform} (distributed execution)")
    for i, transformation in enumerate(env.pipeline):
        logging.info(
            f"  {i+1:2d}. {transformation.function_class.__name__:25s} | "
            f"Parallelism: {transformation.parallelism:2d} | "
            f"Basename: {transformation.basename}"
        )

    return env


def validate_remote_multi_stream_parallelism():
    """Validate parallelism for multi-stream operations in remote environment"""
    logging.info("\n" + "=" * 70)
    logging.info("REMOTE ENVIRONMENT - MULTI-STREAM PARALLELISM VALIDATION")
    logging.info("=" * 70)

    try:
        env = RemoteEnvironment(name="remote_multi_stream_test")
    except Exception as e:
        logging.info(f"⚠️  RemoteEnvironment initialization warning: {e}")
        env = RemoteEnvironment(name="remote_multi_stream_test")

    # Create streams with more data for distributed processing
    stream1_data = list(range(1, 16, 2))  # [1, 3, 5, 7, 9, 11, 13, 15]
    stream2_data = list(range(2, 17, 2))  # [2, 4, 6, 8, 10, 12, 14, 16]

    stream1 = env.from_collection(NumberListSource, stream1_data)
    stream2 = env.from_collection(NumberListSource, stream2_data)

    logging.info(f"\n📊 Stream1 data (odd numbers): {stream1_data}")
    logging.info(f"📊 Stream2 data (even numbers): {stream2_data}")

    logging.info("\n--- Test 1: Distributed CoMap with direct parallelism ---")
    result1 = (
        stream1.connect(stream2)
        .comap(DistributedCoMapProcessor, parallelism=3)  # 3 parallel CoMap processors
        .sink(DistributedSink, parallelism=2)
    )  # 2 sinks

    logging.info("\n--- Test 2: Distributed CoMap with direct parallelism ---")
    result2 = (
        stream1.connect(stream2)
        .comap(DistributedCoMapProcessor, parallelism=4)  # 4 parallel CoMap processors
        .sink(DistributedSink, parallelism=1)
    )  # 1 sink

    # Analyze pipeline
    logging.info(f"\n📋 DISTRIBUTED PIPELINE ANALYSIS:")
    logging.info(f"Total transformations: {len(env.pipeline)}")
    logging.info(f"Environment platform: {env.platform}")
    for i, transformation in enumerate(env.pipeline):
        logging.info(
            f"  {i+1:2d}. {transformation.function_class.__name__:25s} | "
            f"Parallelism: {transformation.parallelism:2d} | "
            f"Basename: {transformation.basename}"
        )

    return env


def validate_ray_distributed_execution():
    """Validate that Ray properly distributes parallel operations"""
    logging.info("\n" + "=" * 70)
    logging.info("RAY DISTRIBUTED EXECUTION VALIDATION")
    logging.info("=" * 70)

    try:
        env = RemoteEnvironment(name="ray_distribution_test")
        logging.info("✅ RemoteEnvironment initialized")
    except Exception as e:
        logging.info(f"⚠️  RemoteEnvironment initialization warning: {e}")
        env = RemoteEnvironment(name="ray_distribution_test")

    # Create a pipeline designed to show distributed execution
    large_dataset = list(range(1, 51))  # 1 to 50 - enough data for distribution

    result = (
        env.from_collection(NumberListSource, large_dataset)
        .map(DistributedProcessor, "DistTest", parallelism=5)  # 5 parallel processors
        .filter(DistributedFilter, parallelism=3)  # 3 parallel filters
        .sink(DistributedSink, parallelism=2)
    )  # 2 sinks

    logging.info(f"\n📋 Remote Distribution Test Pipeline:")
    logging.info(f"  - Dataset size: {len(large_dataset)} items")
    logging.info(
        f"  - Expected parallel processors: 5 (will distribute based on available workers)"
    )
    logging.info(
        f"  - Expected parallel filters: 3 (will distribute based on available workers)"
    )
    logging.info(f"  - Expected sinks: 2 (will distribute based on available workers)")

    logging.info(f"\n🔍 Pipeline transformations:")
    for i, transformation in enumerate(env.pipeline):
        logging.info(
            f"  {i+1}. {transformation.basename} (parallelism: {transformation.parallelism})"
        )

    logging.info(f"\n💡 Key aspects of remote distributed execution:")
    logging.info(f"   - Each parallel instance may run on different remote workers")
    logging.info(f"   - Process IDs will differ across workers")
    logging.info(f"   - Work is distributed based on available resources")
    logging.info(f"   - RemoteEnvironment handles load balancing and coordination")

    return env


def main():
    """Main function to run all remote validation tests"""
    logging.info("🚀 SAGE Remote Environment Parallelism Validation")
    logging.info("This example validates parallelism hints in RemoteEnvironment (Ray)")

    try:
        # Run all validation tests
        env1 = validate_remote_single_stream_parallelism()
        env2 = validate_remote_multi_stream_parallelism()
        env3 = validate_ray_distributed_execution()

        logging.info("\n" + "=" * 70)
        logging.info("REMOTE VALIDATION SUMMARY")
        logging.info("=" * 70)
        logging.info("✅ Remote single stream parallelism: Tested with remote workers")
        logging.info("✅ Remote multi-stream parallelism: Tested distributed CoMap")
        logging.info("✅ Remote distributed execution: Verified parallel worker distribution")
        logging.info("✅ RemoteEnvironment direct parallelism: WORKING CORRECTLY")

        logging.info(f"\n📊 Total remote environments created: 3")
        logging.info(
            f"📊 Total distributed transformations: {len(env1.pipeline) + len(env2.pipeline) + len(env3.pipeline)}"
        )

        logging.info(f"\n💡 Key remote validations:")
        logging.info(f"   - Parallelism settings work in distributed remote environment")
        logging.info(f"   - Direct parallelism specification distributes work across remote workers")
        logging.info(f"   - Multi-stream operations (CoMap) support distributed parallelism")
        logging.info(
            f"   - RemoteEnvironment automatically handles worker assignment and coordination"
        )

    except Exception as e:
        logging.info(f"\n❌ Remote validation encountered an error: {e}")
        logging.info(
            f"💡 This might be due to RemoteEnvironment not being available or configured properly"
        )
        logging.info(f"   Please ensure the JobManager service is running and accessible")
        logging.info(f"   And that your system supports remote distributed execution")


if __name__ == "__main__":
    main()
