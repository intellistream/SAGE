#pragma once

#include <vector>
#include <string>
#include <memory>
#include <cstdint>

namespace sage_db {

// Common types and constants
using VectorId = uint64_t;
using Dimension = uint32_t;
using Score = float;

// Vector data type (float32)
using Vector = std::vector<float>;

// Metadata types
using MetadataValue = std::string;
using Metadata = std::map<std::string, MetadataValue>;

// Query result
struct QueryResult {
    VectorId id;
    Score score;
    Metadata metadata;
    
    QueryResult(VectorId id_, Score score_, const Metadata& metadata_ = {})
        : id(id_), score(score_), metadata(metadata_) {}
};

// Search parameters
struct SearchParams {
    uint32_t k = 10;              // Number of nearest neighbors
    uint32_t nprobe = 1;          // Number of clusters to search (for IVF)
    float radius = -1.0f;         // Radius search (if > 0)
    bool include_metadata = true;  // Whether to include metadata in results
    
    SearchParams() = default;
    SearchParams(uint32_t k_) : k(k_) {}
};

// Index types supported
enum class IndexType {
    FLAT,           // Brute force (exact search)
    IVF_FLAT,       // Inverted file with flat quantizer
    IVF_PQ,         // Inverted file with product quantizer
    HNSW,           // Hierarchical NSW (if available)
    AUTO            // Automatically choose based on data size
};

// Distance metrics
enum class DistanceMetric {
    L2,             // Euclidean distance
    INNER_PRODUCT,  // Inner product (cosine for normalized vectors)
    COSINE          // Cosine distance
};

// Database configuration
struct DatabaseConfig {
    IndexType index_type = IndexType::AUTO;
    DistanceMetric metric = DistanceMetric::L2;
    Dimension dimension = 0;
    
    // IVF specific parameters
    uint32_t nlist = 100;         // Number of clusters for IVF
    uint32_t m = 8;               // Number of subquantizers for PQ
    uint32_t nbits = 8;           // Bits per subquantizer for PQ
    
    // HNSW specific parameters
    uint32_t M = 16;              // Number of connections for HNSW
    uint32_t efConstruction = 200; // Size of dynamic candidate list for HNSW
    
    DatabaseConfig() = default;
    DatabaseConfig(Dimension dim) : dimension(dim) {}
};

// Error types
class SageDBException : public std::exception {
private:
    std::string message;
public:
    explicit SageDBException(const std::string& msg) : message(msg) {}
    const char* what() const noexcept override { return message.c_str(); }
};

} // namespace sage_db
