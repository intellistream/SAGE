#!/usr/bin/env python3
"""
Simple test for queue adapter
"""

import sys
sys.path.insert(0, '/home/shuhao/SAGE')

from sage.utils.queue_adapter import create_queue, get_recommended_queue_backend

def test_queue():
    print("Testing queue adapter...")
    
    # Test backend detection
    backend = get_recommended_queue_backend()
    print(f"Recommended backend: {backend}")
    
    # Test queue creation
    q = create_queue(name='test_queue')
    print(f"Queue created: {type(q)}")
    
    # Test basic operations
    test_data = "hello world"
    print(f"Putting data: {test_data}")
    q.put(test_data)
    
    print("Getting data...")
    result = q.get()
    print(f"Got data: {result}")
    
    # Test nowait operations
    print("Testing nowait operations...")
    q.put_nowait("nowait_test")
    result2 = q.get_nowait()
    print(f"Nowait result: {result2}")
    
    print("Queue test PASSED!")
    return True

if __name__ == "__main__":
    try:
        test_queue()
    except Exception as e:
        print(f"Queue test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
