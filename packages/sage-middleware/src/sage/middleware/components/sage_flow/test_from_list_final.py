import sys
sys.path.insert(0, 'python')
import sage_flow_datastream as sfd

print('Testing from_list function:')
test_data = [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}]
print('Test data:', test_data)

try:
    result = sfd.from_list(test_data)
    print('Success! Result:', result)
    print('Result type:', type(result))
except Exception as e:
    print('Error:', e)
    print('Error type:', type(e))