#!/usr/bin/env python3
"""
Client Test Script for Remote Environment Submission
Tests serialization integrity by sending environment objects to the test server.
"""

import socket
import logging
import sys
import time
import traceback

try:
    import dill as serializer
    print("Using dill for serialization")
except ImportError:
    import pickle as serializer
    print("Warning: Could not import dill, using pickle as fallback")

# Add sage module to path for testing
sys.path.insert(0, '/home/tjy/SAGE')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockJobManagerClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        logger.info(f"MockJobManagerClient connecting to {host}:{port}")
    
    def health_check(self):
        return {"status": "success", "message": "Mock client is healthy"}

class MockJobManager:
    def __init__(self):
        self.name = "mock_jobmanager"
        logger.info("MockJobManager initialized")

class MockBaseEnvironment:
    """Mock base environment class for testing."""
    
    def __init__(self, name, platform='remote'):
        self.name = name
        self.platform = platform
        self.config = {
            'batch_size': 100,
            'timeout': 30,
            'retry_count': 3
        }
        logger.info(f"MockBaseEnvironment '{name}' initialized with platform '{platform}'")
    
    def get_status(self):
        return {"name": self.name, "platform": self.platform, "status": "ready"}

class SimpleRemoteEnvironment(MockBaseEnvironment):
    """Simplified Remote Environment - only serializes and submits to remote JobManager."""
    
    # Exclude these attributes from serialization
    __state_exclude__ = [
        '_engine_client',
        '_jobmanager', 
        'client',
        'jobmanager'
    ]
    
    def __init__(self, name, host='127.0.0.1', port=19001):
        super().__init__(name, platform='remote')
        self.host = host
        self.port = port
        
        # Initialize configuration
        self.config.update({
            'engine_host': host,
            'engine_port': port,
        })
        
        # Internal connection objects - will be excluded from serialization
        self._engine_client = None
        self._jobmanager = None
        
        logger.info(f"SimpleRemoteEnvironment '{name}' initialized for {host}:{port}")
    
    @property
    def client(self):
        """Lazy initialization of client connection."""
        if self._engine_client is None:
            self._engine_client = MockJobManagerClient(self.host, self.port)
        return self._engine_client
    
    @property
    def jobmanager(self):
        """Lazy initialization of jobmanager."""
        if self._jobmanager is None:
            self._jobmanager = MockJobManager()
        return self._jobmanager
    
    def __repr__(self):
        return f"SimpleRemoteEnvironment(name='{self.name}', host='{self.host}', port={self.port})"

def send_to_server(host, port, data):
    """Send serialized data to the test server."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
            
            # Send data length first
            data_length = len(data).to_bytes(4, byteorder='big')
            sock.sendall(data_length)
            
            # Send the actual data
            sock.sendall(data)
            
            # Receive response
            response_length = int.from_bytes(sock.recv(4), byteorder='big')
            response_data = b''
            while len(response_data) < response_length:
                chunk = sock.recv(response_length - len(response_data))
                if not chunk:
                    break
                response_data += chunk
            
            response = serializer.loads(response_data)
            return response
            
    except Exception as e:
        logger.error(f"Error sending to server: {str(e)}")
        return {"status": "error", "message": str(e)}

def main():
    """Test client submission to the environment test server."""
    
    logger.info("Starting client submission test")
    
    # Create test environment
    env = SimpleRemoteEnvironment("client_test_env", host="127.0.0.1", port=19001)
    logger.info(f"Created environment: {env}")
    
    try:
        # Test basic functionality before serialization
        logger.info("Testing environment before serialization:")
        logger.info(f"  Client: {env.client}")
        logger.info(f"  JobManager: {env.jobmanager}")
        logger.info(f"  Config: {env.config}")
        
        # Serialize the environment
        logger.info("Serializing environment for transmission...")
        serialized_data = serializer.dumps(env)
        logger.info(f"Serialized data size: {len(serialized_data)} bytes")
        
        # Send to test server
        logger.info("Sending environment to test server on 127.0.0.1:19002")
        response = send_to_server("127.0.0.1", 19002, serialized_data)
        
        if response["status"] == "success":
            logger.info("✅ Environment submission successful!")
            logger.info(f"Server response: {response}")
        else:
            logger.error(f"❌ Environment submission failed: {response}")
            
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        traceback.print_exc()
    
    logger.info("Client test completed")

if __name__ == "__main__":
    # Wait a moment for server to be ready
    time.sleep(1)
    main()
