#!/usr/bin/env python3
"""
SAGE Flow Python API Demonstration
Demonstrates the index system bindings following TODO.md requirements
"""

import sys
import os
import numpy as np

# Add the build directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'build'))

import sage_flow_py

def demonstrate_index_configuration():
    """Demonstrate index configuration according to TODO.md API requirements"""
    print("📋 Index Configuration Demo:")
    print("=" * 50)
    
    # Create different index configurations
    configs = {
        "HNSW": {
            "type": sage_flow_py.IndexType.HNSW,
            "params": {"hnsw_m_": 16, "hnsw_ef_construction_": 200, "hnsw_ef_search_": 100}
        },
        "IVF": {
            "type": sage_flow_py.IndexType.IVF,
            "params": {"ivf_nlist_": 100, "ivf_nprobe_": 10}
        },
        "Vamana": {
            "type": sage_flow_py.IndexType.VAMANA,
            "params": {}  # Vamana-specific params would be added when implemented
        }
    }
    
    for name, config_info in configs.items():
        config = sage_flow_py.IndexConfig()
        config.type_ = config_info["type"]
        
        # Set parameters
        for param, value in config_info["params"].items():
            setattr(config, param, value)
        
        print(f"  ✅ {name} Index Configuration:")
        print(f"     Type: {config.type_}")
        for param, value in config_info["params"].items():
            print(f"     {param}: {getattr(config, param)}")
        print()

def demonstrate_search_results():
    """Demonstrate SearchResult handling for vector similarity search"""
    print("🎯 Search Results Demo:")
    print("=" * 50)
    
    # Simulate search results from different indexes
    results = [
        sage_flow_py.SearchResult(1001, 0.1, 0.95),  # id, distance, similarity
        sage_flow_py.SearchResult(2002, 0.3, 0.85),
        sage_flow_py.SearchResult(3003, 0.5, 0.75),
        sage_flow_py.SearchResult(1004, 0.7),  # Using simplified constructor
        sage_flow_py.SearchResult(2005, 0.9),
    ]
    
    print("  Search Results (sorted by distance):")
    for i, result in enumerate(results, 1):
        print(f"    {i}. {result}")
        print(f"       ID: {result.id_}, Distance: {result.distance_:.3f}, Similarity: {result.similarity_score_:.3f}")
    print()

def demonstrate_multimodal_processing():
    """Demonstrate multimodal message processing following SAGE Flow patterns"""
    print("🎭 Multimodal Processing Demo:")
    print("=" * 50)
    
    # Create different types of messages
    text_msg = sage_flow_py.create_text_message(1001, "This is a sample text for embedding generation")
    binary_data = [0x48, 0x65, 0x6C, 0x6C, 0x6F]  # "Hello" in bytes as list of ints
    binary_msg = sage_flow_py.create_binary_message(1002, binary_data)
    
    print(f"  📝 Text Message:")
    print(f"     UID: {text_msg.get_uid()}")
    print(f"     Content Type: {text_msg.get_content_type()}")
    print(f"     Content: {text_msg.get_content_as_string()}")
    print(f"     Has Embedding: {text_msg.has_embedding()}")
    print()
    
    print(f"  🔢 Binary Message:")
    print(f"     UID: {binary_msg.get_uid()}")
    print(f"     Content Type: {binary_msg.get_content_type()}")
    print(f"     Binary Size: {len(binary_msg.get_content_as_binary())} bytes")
    print(f"     Has Embedding: {binary_msg.has_embedding()}")
    print()
    
    # Demonstrate embedding handling
    embedding_vector = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    vector_data = sage_flow_py.VectorData(embedding_vector, len(embedding_vector))
    
    # Set embedding for text message
    text_msg.set_embedding(vector_data)
    print(f"  ✅ Added embedding to text message:")
    print(f"     Has Embedding: {text_msg.has_embedding()}")
    if text_msg.has_embedding():
        embedding = text_msg.get_embedding()
        print(f"     Embedding Dimension: {embedding.get_dimension()}")
        print(f"     Embedding Size: {embedding.size()}")
    print()

def demonstrate_vector_operations():
    """Demonstrate vector operations for similarity calculations"""
    print("🔢 Vector Operations Demo:")
    print("=" * 50)
    
    # Create sample vectors
    vec1_data = [1.0, 2.0, 3.0, 4.0]
    vec2_data = [2.0, 3.0, 4.0, 5.0]
    
    vec1 = sage_flow_py.VectorData(vec1_data, len(vec1_data))
    vec2 = sage_flow_py.VectorData(vec2_data, len(vec2_data))
    
    print(f"  Vector 1: {vec1_data}")
    print(f"  Vector 2: {vec2_data}")
    print()
    
    # Calculate similarities
    dot_product = vec1.dot_product(vec2)
    cosine_sim = vec1.cosine_similarity(vec2)
    euclidean_dist = vec1.euclidean_distance(vec2)
    
    print(f"  🔹 Dot Product: {dot_product:.3f}")
    print(f"  🔹 Cosine Similarity: {cosine_sim:.3f}")
    print(f"  🔹 Euclidean Distance: {euclidean_dist:.3f}")
    print()

def demonstrate_api_compatibility():
    """Demonstrate API compatibility with SAGE ecosystem requirements"""
    print("🔧 API Compatibility Demo:")
    print("=" * 50)
    
    print("  ✅ Available Index Types:")
    index_types = [
        ("BRUTE_FORCE", sage_flow_py.IndexType.BRUTE_FORCE),
        ("HNSW", sage_flow_py.IndexType.HNSW), 
        ("IVF", sage_flow_py.IndexType.IVF),
        ("VAMANA", sage_flow_py.IndexType.VAMANA),
        ("DYNA_GRAPH", sage_flow_py.IndexType.DYNA_GRAPH),
        ("ADA_IVF", sage_flow_py.IndexType.ADA_IVF),
        ("FRESH_VAMANA", sage_flow_py.IndexType.FRESH_VAMANA),
        ("SP_FRESH", sage_flow_py.IndexType.SP_FRESH),
        ("VECTRA_FLOW", sage_flow_py.IndexType.VECTRA_FLOW),
    ]
    
    for name, index_type in index_types:
        print(f"     - {name}: {index_type}")
    print()
    
    print("  📊 Configuration Support:")
    config = sage_flow_py.IndexConfig()
    config_attrs = [
        "type_", "hnsw_m_", "hnsw_ef_construction_", "hnsw_ef_search_",
        "ivf_nlist_", "ivf_nprobe_"
    ]
    
    for attr in config_attrs:
        if hasattr(config, attr):
            print(f"     ✅ {attr}: {getattr(config, attr)}")
    print()
    
    print("  🎭 Content Type Support:")
    content_types = [
        ("TEXT", sage_flow_py.ContentType.TEXT),
        ("IMAGE", sage_flow_py.ContentType.IMAGE),
        ("AUDIO", sage_flow_py.ContentType.AUDIO),
        ("VIDEO", sage_flow_py.ContentType.VIDEO),
        ("BINARY", sage_flow_py.ContentType.BINARY),
    ]
    
    for name, content_type in content_types:
        print(f"     - {name}: {content_type}")
    print()

def main():
    """Main demonstration function"""
    print("🚀 SAGE Flow Python API Demonstration")
    print("=====================================")
    print("Demonstrating index system bindings according to TODO.md requirements\n")
    
    try:
        demonstrate_index_configuration()
        demonstrate_search_results()
        demonstrate_multimodal_processing()
        demonstrate_vector_operations()
        demonstrate_api_compatibility()
        
        print("🎉 All demonstrations completed successfully!")
        print("\n📝 Next Steps (from TODO.md):")
        print("   - Implement concrete index classes (HNSW, IVF, Vamana, etc.)")
        print("   - Add MemoryPool integration")
        print("   - Implement LocalEnvironment and RemoteEnvironment compatibility")
        print("   - Add streaming pipeline support")
        print("   - Integrate with sage_memory and sage_libs")
        
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
