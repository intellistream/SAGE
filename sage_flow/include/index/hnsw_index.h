#pragma once

#include <memory>
#include <unordered_map>
#include <vector>
#include "index.h"

namespace sage_flow {

/**
 * @brief Hierarchical Navigable Small World (HNSW) index implementation
 * Reference: flow_old/include/index/index.h
 */
class HnswIndex : public Index {
 public:
  explicit HnswIndex(std::shared_ptr<MemoryPool> memory_pool)
      : Index(std::move(memory_pool)) {}

  ~HnswIndex() override = default;

  // Prevent copying
  HnswIndex(const HnswIndex&) = delete;
  auto operator=(const HnswIndex&) -> HnswIndex& = delete;

  // Allow moving
  HnswIndex(HnswIndex&&) = default;
  auto operator=(HnswIndex&&) -> HnswIndex& = default;

  /**
   * @brief Initialize the HNSW index
   * @param config Index configuration parameters
   * @return true if initialization successful
   */
  auto Initialize(const IndexConfig& config) -> bool override;

  /**
   * @brief Add vector to the index
   * @param id Unique identifier for the vector
   * @param vector Vector data
   * @return true if addition successful
   */
  auto AddVector(uint64_t id, const std::vector<float>& vector) -> bool override;

  /**
   * @brief Remove vector from the index
   * @param id Unique identifier for the vector to remove
   * @return true if removal successful
   */
  auto RemoveVector(uint64_t id) -> bool override;

  /**
   * @brief Search for k nearest neighbors using HNSW algorithm
   * @param query_vector Query vector
   * @param k Number of nearest neighbors to return
   * @return Vector of search results
   */
  auto Search(const std::vector<float>& query_vector, size_t k) const 
      -> std::vector<SearchResult> override;

  /**
   * @brief Build the HNSW index after adding vectors
   * @return true if building successful
   */
  auto Build() -> bool override;

  /**
   * @brief Save index to file
   * @param file_path Path to save the index
   * @return true if saving successful
   */
  auto SaveIndex(const std::string& file_path) const -> bool override;

  /**
   * @brief Load index from file
   * @param file_path Path to load the index from
   * @return true if loading successful
   */
  auto LoadIndex(const std::string& file_path) -> bool override;

  /**
   * @brief Get the current size of the index
   * @return Number of vectors in the index
   */
  auto Size() const -> size_t override;

  /**
   * @brief Clear all data from the index
   */
  void Clear() override;

  /**
   * @brief Get index type
   * @return IndexType::kHnsw
   */
  auto GetType() const -> IndexType override;

 private:
  struct HnswNode {
    uint64_t id_;
    std::vector<float> vector_;
    std::vector<std::vector<uint64_t>> connections_;  // connections[level] = neighbor_ids
    size_t level_;
    
    HnswNode(uint64_t id, std::vector<float> vector, size_t level)
        : id_(id), vector_(std::move(vector)), level_(level) {
      connections_.resize(level + 1);
    }
  };
  
  IndexConfig config_;
  std::unordered_map<uint64_t, std::unique_ptr<HnswNode>> nodes_;
  uint64_t entry_point_id_ = 0;
  bool is_built_ = false;
  
  /**
   * @brief Get random level for new node
   * @return Random level following exponential decay
   */
  auto GetRandomLevel() const -> size_t;
  
  /**
   * @brief Calculate distance between two vectors
   * @param vec1 First vector
   * @param vec2 Second vector
   * @return Distance value
   */
  auto CalculateDistance(const std::vector<float>& vec1, 
                        const std::vector<float>& vec2) const -> float;
  
  /**
   * @brief Search for entry points at a specific level
   * @param query Query vector
   * @param entry_points Starting points
   * @param num_closest Number of closest points to return
   * @param level Level to search at
   * @return Vector of closest node IDs
   */
  auto SearchLayer(const std::vector<float>& query,
                   const std::vector<uint64_t>& entry_points,
                   size_t num_closest,
                   size_t level) const -> std::vector<uint64_t>;
                   
  /**
   * @brief Select M neighbors for a node at given level
   * @param candidates Candidate neighbors
   * @param m Number of neighbors to select
   * @return Selected neighbor IDs
   */
  auto SelectNeighbors(const std::vector<uint64_t>& candidates, size_t m) const 
      -> std::vector<uint64_t>;
};

}  // namespace sage_flow
