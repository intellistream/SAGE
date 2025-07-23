#pragma once

#include <cstdint>
#include <string>

namespace sage_flow {

/**
 * @brief Index types supported in SAGE flow
 * Extended from DynaGraph IndexType enum
 */
enum class IndexType : std::uint8_t {
  kNone,
  kBruteForce,  // Brute force search
  kHnsw,        // Hierarchical Navigable Small World
  kIvf,         // Inverted File Index
  kAdaIvf,      // Adaptive Inverted File Index
  kVectraFlow,  // Custom vector flow index
  kVamana,      // Vamana graph index
  kFreshVamana, // Fresh Vamana with incremental updates
  kDynaGraph,   // Dynamic graph index
  kSpFresh,     // Streaming processing fresh index
  kKnn          // K-Nearest Neighbors (legacy)
};

/**
 * @brief Index configuration parameters
 */
struct IndexConfig {
  IndexType type_ = IndexType::kBruteForce;
  size_t dimension_ = 128;                    // Vector dimension
  size_t max_elements_ = 100000;             // Maximum number of elements
  std::string distance_metric_ = "cosine";   // Distance metric: cosine, euclidean, dot
  
  // HNSW specific parameters
  size_t hnsw_m_ = 16;                       // Number of connections for HNSW
  size_t hnsw_ef_construction_ = 200;        // Size of dynamic candidate list during construction
  size_t hnsw_ef_search_ = 50;               // Size of dynamic candidate list during search
  
  // IVF specific parameters
  size_t ivf_nlist_ = 100;                   // Number of inverted lists
  size_t ivf_nprobe_ = 10;                   // Number of lists to search
};

/**
 * @brief Search result structure
 */
struct SearchResult {
  uint64_t id_;
  float distance_;
  float similarity_score_;
  
  // Default constructor for container operations
  SearchResult() : id_(0), distance_(0.0F), similarity_score_(0.0F) {}
  
  // Full constructor
  SearchResult(uint64_t id_val, float dist, float sim)
      : id_(id_val), distance_(dist), similarity_score_(sim) {}
      
  // Simplified constructor for distance-only results
  SearchResult(uint64_t id_val, float dist)
      : id_(id_val), distance_(dist), similarity_score_(1.0F / (1.0F + dist)) {}
};

}  // namespace sage_flow
