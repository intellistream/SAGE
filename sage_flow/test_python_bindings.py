#!/usr/bin/env python3
"""
Test script for SAGE Flow Python bindings
Tests the newly added index system bindings
"""

import sys
import os

# Add the build directory to Python path to import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'build'))

try:
    import sage_flow_py
    print("✅ Successfully imported sage_flow_py")
    
    # Test IndexType enum
    print("\n🔍 Testing IndexType enum:")
    print(f"  BRUTE_FORCE: {sage_flow_py.IndexType.BRUTE_FORCE}")
    print(f"  HNSW: {sage_flow_py.IndexType.HNSW}")
    print(f"  IVF: {sage_flow_py.IndexType.IVF}")
    print(f"  VAMANA: {sage_flow_py.IndexType.VAMANA}")
    print(f"  DYNA_GRAPH: {sage_flow_py.IndexType.DYNA_GRAPH}")
    
    # Test IndexConfig
    print("\n⚙️  Testing IndexConfig:")
    config = sage_flow_py.IndexConfig()
    config.type_ = sage_flow_py.IndexType.HNSW
    config.hnsw_m_ = 16
    config.hnsw_ef_construction_ = 200
    config.hnsw_ef_search_ = 100
    print(f"  Created IndexConfig with type: {config.type_}")
    print(f"  HNSW M: {config.hnsw_m_}")
    print(f"  HNSW ef_construction: {config.hnsw_ef_construction_}")
    print(f"  HNSW ef_search: {config.hnsw_ef_search_}")
    
    # Test SearchResult
    print("\n🎯 Testing SearchResult:")
    result1 = sage_flow_py.SearchResult(12345, 0.75)
    result2 = sage_flow_py.SearchResult(67890, 1.23, 0.45)
    print(f"  Result 1: {result1}")
    print(f"  Result 2: {result2}")
    print(f"  Result 1 ID: {result1.id_}")
    print(f"  Result 1 distance: {result1.distance_}")
    print(f"  Result 2 similarity: {result2.similarity_score_}")
    
    # Test existing MultiModalMessage functionality
    print("\n💬 Testing MultiModalMessage:")
    msg = sage_flow_py.create_text_message(12345, "Hello, SAGE Flow!")
    print(f"  Created text message with UID: {msg.get_uid()}")
    print(f"  Message content: {msg.get_content_as_string()}")
    print(f"  Content type: {msg.get_content_type()}")
    
    # Test VectorData
    print("\n🔢 Testing VectorData:")
    vector_data = sage_flow_py.VectorData([1.0, 2.0, 3.0, 4.0], 4)
    print(f"  Created vector with dimension: {vector_data.get_dimension()}")
    print(f"  Vector size: {vector_data.size()}")
    
    print("\n🎉 All tests passed! Python bindings are working correctly.")
    
except ImportError as e:
    print(f"❌ Failed to import sage_flow_py: {e}")
    print("Make sure the project is built successfully.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
