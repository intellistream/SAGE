#!/usr/bin/env python3
"""
Fix for CoMap service call timeout issue
Diagnoses and fixes the timing issue where service calls are made before service tasks are started
"""

import time
from sage.core.api.local_environment import LocalEnvironment
from sage.core.function.source_function import SourceFunction
from sage.core.function.comap_function import BaseCoMapFunction
from sage.core.function.sink_function import SinkFunction

# Simple test services
class TestService:
    def hello(self, data):
        return f"Hello from service: {data}"

# Simple test sources
class TestSource(SourceFunction):
    def __init__(self, ctx=None, **kwargs):
        super().__init__(ctx=ctx, **kwargs)
        self.counter = 0
        
    def execute(self):
        if self.counter >= 2:
            return None
        
        data = f"test_data_{self.counter}"
        self.counter += 1
        return data

# Simple CoMap function with service calls
class SimpleCoMapFunction(BaseCoMapFunction):
    def map0(self, data):
        print(f"[DEBUG] Map0 called with: {data}")
        print(f"[DEBUG] About to call service...")
        
        # This should not block if services are properly started
        result = self.call_service["test_service"].hello(data)
        print(f"[DEBUG] Service call succeeded: {result}")
        
        return {"stream": 0, "data": data, "service_result": result}
    
    def map1(self, data):
        print(f"[DEBUG] Map1 called with: {data}")
        # No service call in map1
        return {"stream": 1, "data": data}

# Simple sink to collect results
class TestSink(SinkFunction):
    results = []
    
    def execute(self, data):
        print(f"[DEBUG] Sink received: {data}")
        TestSink.results.append(data)
        return data

def test_service_call_timing():
    """Test service call timing issue"""
    print("🚀 Testing Service Call Timing Fix")
    print("=" * 50)
    
    # Clear previous results
    TestSink.results.clear()
    
    # Create environment and register service
    env = LocalEnvironment("service_timing_test")
    env.register_service("test_service", TestService)
    
    print("✅ Service registered")
    
    # Create sources and CoMap pipeline
    source1 = env.from_source(TestSource, delay=0.1)
    source2 = env.from_source(TestSource, delay=0.1)
    
    result = (source1
              .connect(source2)
              .comap(SimpleCoMapFunction)
              .sink(TestSink))
    
    print("✅ Pipeline created")
    
    try:
        # Submit the job (this creates and starts services)
        env.submit()
        print("✅ Job submitted - services should be starting...")
        
        # CRITICAL: Wait longer for services to fully start before data flows
        print("⏳ Waiting 3 seconds for services to fully start...")
        time.sleep(3)
        
        print("✅ Services should be fully started now")
        print("📊 Pipeline running, waiting for results...")
        
        # Wait for data processing
        time.sleep(5)
        
    finally:
        env.close()
    
    # Check results
    print(f"\n📋 Results collected: {len(TestSink.results)}")
    for i, result in enumerate(TestSink.results):
        print(f"  Result {i+1}: {result}")
    
    # Verify service calls worked
    service_results = [r for r in TestSink.results if 'service_result' in r]
    print(f"\n✅ Service calls completed: {len(service_results)}")
    
    if len(service_results) > 0:
        print("🎉 SUCCESS: Service calls are working!")
        return True
    else:
        print("❌ FAILURE: No service calls completed")
        return False

if __name__ == "__main__":
    success = test_service_call_timing()
    if not success:
        exit(1)
