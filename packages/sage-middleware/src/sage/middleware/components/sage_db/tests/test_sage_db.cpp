#include "sage_db/sage_db.h"
#include <iostream>
#include <random>
#include <chrono>
#include <cassert>

using namespace sage_db;

void test_basic_operations() {
    std::cout << "Testing basic operations..." << std::endl;
    
    DatabaseConfig config(128);
    config.index_type = IndexType::FLAT;
    config.metric = DistanceMetric::L2;
    
    SageDB db(config);
    
    // Test adding vectors
    Vector vec1(128, 0.1f);
    Vector vec2(128, 0.2f);
    Vector vec3(128, 0.3f);
    
    Metadata meta1 = {{"category", "A"}, {"text", "first vector"}};
    Metadata meta2 = {{"category", "B"}, {"text", "second vector"}};
    Metadata meta3 = {{"category", "A"}, {"text", "third vector"}};
    
    VectorId id1 = db.add(vec1, meta1);
    VectorId id2 = db.add(vec2, meta2);
    VectorId id3 = db.add(vec3, meta3);
    
    assert(id1 != id2 && id2 != id3);
    assert(db.size() == 3);
    
    // Test search
    auto results = db.search(vec1, 2);
    assert(results.size() == 2);
    assert(results[0].id == id1); // Should find itself first
    
    std::cout << "✅ Basic operations test passed" << std::endl;
}

void test_metadata_operations() {
    std::cout << "Testing metadata operations..." << std::endl;
    
    DatabaseConfig config(64);
    SageDB db(config);
    
    Vector vec(64, 1.0f);
    Metadata meta = {{"type", "test"}, {"value", "123"}};
    
    VectorId id = db.add(vec, meta);
    
    // Test metadata retrieval
    Metadata retrieved_meta;
    bool found = db.get_metadata(id, retrieved_meta);
    assert(found);
    assert(retrieved_meta["type"] == "test");
    assert(retrieved_meta["value"] == "123");
    
    // Test metadata search
    auto ids = db.find_by_metadata("type", "test");
    assert(ids.size() == 1);
    assert(ids[0] == id);
    
    std::cout << "✅ Metadata operations test passed" << std::endl;
}

void test_batch_operations() {
    std::cout << "Testing batch operations..." << std::endl;
    
    DatabaseConfig config(32);
    SageDB db(config);
    
    // Create batch data
    std::vector<Vector> vectors;
    std::vector<Metadata> metadata;
    
    for (int i = 0; i < 10; ++i) {
        Vector vec(32, static_cast<float>(i) * 0.1f);
        vectors.push_back(vec);
        
        Metadata meta = {{"index", std::to_string(i)}, {"batch", "test"}};
        metadata.push_back(meta);
    }
    
    // Add batch
    auto ids = db.add_batch(vectors, metadata);
    assert(ids.size() == 10);
    assert(db.size() == 10);
    
    // Test batch search
    Vector query(32, 0.05f); // Should be close to vector with index 0 or 1
    auto results = db.search(query, 3);
    assert(results.size() == 3);
    
    std::cout << "✅ Batch operations test passed" << std::endl;
}

void test_filtered_search() {
    std::cout << "Testing filtered search..." << std::endl;
    
    DatabaseConfig config(16);
    SageDB db(config);
    
    // Add vectors with different categories
    for (int i = 0; i < 20; ++i) {
        Vector vec(16, static_cast<float>(i) * 0.1f);
        Metadata meta = {{"category", (i % 2 == 0) ? "even" : "odd"}};
        db.add(vec, meta);
    }
    
    // Search with filter
    Vector query(16, 0.5f);
    SearchParams params;
    params.k = 10;
    
    auto filter_even = [](const Metadata& meta) {
        auto it = meta.find("category");
        return it != meta.end() && it->second == "even";
    };
    
    auto results = db.filtered_search(query, params, filter_even);
    
    // All results should be even category
    for (const auto& result : results) {
        assert(result.metadata.at("category") == "even");
    }
    
    std::cout << "✅ Filtered search test passed" << std::endl;
}

void test_persistence() {
    std::cout << "Testing persistence..." << std::endl;
    
    const std::string filepath = "/tmp/test_sage_db";
    
    {
        // Create and populate database
        DatabaseConfig config(8);
        SageDB db(config);
        
        Vector vec1(8, 1.0f);
        Vector vec2(8, 2.0f);
        
        Metadata meta1 = {{"name", "first"}};
        Metadata meta2 = {{"name", "second"}};
        
        db.add(vec1, meta1);
        db.add(vec2, meta2);
        
        // Save
        db.save(filepath);
    }
    
    {
        // Load and verify
        DatabaseConfig config(8);
        SageDB db(config);
        db.load(filepath);
        
        assert(db.size() == 2);
        
        Vector query(8, 1.1f);
        auto results = db.search(query, 1);
        assert(results.size() == 1);
        assert(results[0].metadata.at("name") == "first");
    }
    
    std::cout << "✅ Persistence test passed" << std::endl;
}

void benchmark_performance() {
    std::cout << "Running performance benchmark..." << std::endl;
    
    const int num_vectors = 10000;
    const int dimension = 128;
    const int num_queries = 100;
    
    DatabaseConfig config(dimension);
    config.index_type = IndexType::IVF_FLAT;
    config.nlist = 100;
    
    SageDB db(config);
    
    // Generate random data
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<float> dis(-1.0f, 1.0f);
    
    std::vector<Vector> vectors;
    vectors.reserve(num_vectors);
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // Add vectors
    for (int i = 0; i < num_vectors; ++i) {
        Vector vec(dimension);
        for (int j = 0; j < dimension; ++j) {
            vec[j] = dis(gen);
        }
        vectors.push_back(vec);
        
        Metadata meta = {{"id", std::to_string(i)}};
        db.add(vec, meta);
    }
    
    auto add_time = std::chrono::high_resolution_clock::now();
    
    // Train index
    db.train_index();
    db.build_index();
    
    auto train_time = std::chrono::high_resolution_clock::now();
    
    // Perform searches
    SearchParams params;
    params.k = 10;
    
    for (int i = 0; i < num_queries; ++i) {
        Vector query(dimension);
        for (int j = 0; j < dimension; ++j) {
            query[j] = dis(gen);
        }
        auto results = db.search(query, params);
        assert(results.size() <= params.k);
    }
    
    auto search_time = std::chrono::high_resolution_clock::now();
    
    // Print timing results
    auto add_duration = std::chrono::duration_cast<std::chrono::milliseconds>(add_time - start_time);
    auto train_duration = std::chrono::duration_cast<std::chrono::milliseconds>(train_time - add_time);
    auto search_duration = std::chrono::duration_cast<std::chrono::milliseconds>(search_time - train_time);
    
    std::cout << "📊 Performance Results:" << std::endl;
    std::cout << "   Add " << num_vectors << " vectors: " << add_duration.count() << " ms" << std::endl;
    std::cout << "   Train index: " << train_duration.count() << " ms" << std::endl;
    std::cout << "   " << num_queries << " searches: " << search_duration.count() << " ms" << std::endl;
    std::cout << "   Average search time: " << static_cast<double>(search_duration.count()) / num_queries << " ms" << std::endl;
}

int main() {
    std::cout << "🧪 SAGE DB Test Suite" << std::endl;
    std::cout << "=====================" << std::endl;
    
    try {
        test_basic_operations();
        test_metadata_operations();
        test_batch_operations();
        test_filtered_search();
        test_persistence();
        benchmark_performance();
        
        std::cout << std::endl;
        std::cout << "🎉 All tests passed!" << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "❌ Test failed: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}
