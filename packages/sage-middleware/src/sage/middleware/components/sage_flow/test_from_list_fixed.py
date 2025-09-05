import sys
sys.path.insert(0, 'python')
import sage_flow_datastream as sfd

print('Testing from_list function with correct C++ types:')

# Create test data in the format expected by C++
test_data = [
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 25}
]

print('Test data:', test_data)

try:
    # Try calling with just the data (should use default engine)
    result = sfd.DataStream.from_list(test_data)
    print('Success! Result:', result)
    print('Result type:', type(result))
except Exception as e:
    print('Error:', e)
    print('Error type:', type(e))