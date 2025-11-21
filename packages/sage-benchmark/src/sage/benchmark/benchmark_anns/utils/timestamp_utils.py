"""
Utility functions for timestamp generation and latency analysis
"""
import numpy as np
import pandas as pd
import os


def generate_timestamps(rows, event_rate=4000):
    """
    Generate uniformly increasing event timestamps.
    
    Args:
        rows: Number of rows/events
        event_rate: Events per second (Hz)
    
    Returns:
        numpy array of event timestamps in microseconds
    """
    interval_micros = int(1e6 / event_rate)
    event_timestamps = np.arange(0, rows * interval_micros, interval_micros, dtype=np.int64)
    return event_timestamps


def get_latency_percentile(fraction, event_time, processed_time):
    """
    Calculate latency percentile from event and processed time arrays.
    
    Args:
        fraction: Percentile in range [0, 1]
        event_time: Array of event arrival timestamps
        processed_time: Array of processed timestamps
    
    Returns:
        Latency value at the specified percentile (in microseconds)
    """
    valid_latency = (processed_time - event_time)[
        (processed_time >= event_time) & (processed_time != 0)
    ]
    
    if valid_latency.size == 0:
        print("No valid latency found")
        return 0
    
    valid_latency_sorted = np.sort(valid_latency)
    idx = int(len(valid_latency_sorted) * fraction)
    idx = min(idx, len(valid_latency_sorted) - 1)
    
    return valid_latency_sorted[idx].item()


def store_timestamps_to_csv(filename, ids, event_timestamps, arrival_timestamps, 
                            processed_timestamps, count):
    """
    Store timestamps and IDs into a CSV file.
    
    Args:
        filename: Base filename for the CSV
        ids: Array of vector IDs
        event_timestamps: Array of event timestamps
        arrival_timestamps: Array of arrival timestamps
        processed_timestamps: Array of processed timestamps
        count: Counter for filename suffix
    """
    df = pd.DataFrame({
        'id': ids,
        'eventTime': event_timestamps,
        'arrivalTime': arrival_timestamps,
        'processedTime': processed_timestamps
    })
    
    head, tail = os.path.split(filename)
    if head and not os.path.isdir(head):
        os.makedirs(head)
    
    output_filename = f"{filename}_{count}_timestamps.csv"
    df.to_csv(output_filename, index=False)
    print(f"Timestamps saved to {output_filename}")


def calculate_throughput(num_operations, time_us):
    """
    Calculate throughput in operations per second.
    
    Args:
        num_operations: Number of operations completed
        time_us: Time elapsed in microseconds
    
    Returns:
        Throughput in ops/sec
    """
    if time_us <= 0:
        return 0.0
    return (num_operations * 1e6) / time_us


def calculate_statistics(data):
    """
    Calculate basic statistics (mean, std, percentiles) for an array.
    
    Args:
        data: Numpy array or list of numerical values
    
    Returns:
        Dictionary with statistics
    """
    if len(data) == 0:
        return {
            'mean': 0,
            'std': 0,
            'min': 0,
            'max': 0,
            'p50': 0,
            'p95': 0,
            'p99': 0
        }
    
    arr = np.array(data)
    return {
        'mean': float(np.mean(arr)),
        'std': float(np.std(arr)),
        'min': float(np.min(arr)),
        'max': float(np.max(arr)),
        'p50': float(np.percentile(arr, 50)),
        'p95': float(np.percentile(arr, 95)),
        'p99': float(np.percentile(arr, 99))
    }
