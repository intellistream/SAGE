#!/usr/bin/env python3
import sys
import os
import logging

# Add SAGE to path
sys.path.insert(0, '/home/shuhao/SAGE')

from sage.core.api.remote_environment import RemoteEnvironment
from sage.core.function.map_function import MapFunction
from sage.lib.io.source import FileSource
from sage.lib.io.sink import TerminalSink

class SimpleMapFunction(MapFunction):
    """A simple pure Python map function that avoids Cython issues"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
    
    def execute(self, data):
        """Simple processing function"""
        self.counter += 1
        result = f"Processed item {self.counter}: {data}"
        print(f"Processing: {data} -> {result}")
        return result

def test_remote_simple():
    print("Testing simple remote job submission...")
    
    try:
        # Create remote environment
        env = RemoteEnvironment(name="test_simple", host="localhost", port=19001)
        
        # Create a simple pipeline with pure Python functions
        source = env.from_source(FileSource, {
            "file_path": "/home/shuhao/SAGE/data/q.txt",
            "read_mode": "lines"
        })
        
        # Use our simple map function
        processed = source.map(SimpleMapFunction, {})
        
        # Output to terminal
        processed.sink(TerminalSink, {})
        
        # Submit the job
        print("Submitting remote job...")
        job_uuid = env.submit()
        print(f"Job submitted successfully with UUID: {job_uuid}")
        
        return job_uuid
        
    except Exception as e:
        print(f"Error during remote submission: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_remote_simple()