#pragma once

#include <unordered_map>
#include <vector>
#include "index.h"

namespace sage_flow {

/**
 * @brief Brute force index implementation for exact search
 * Reference: flow_old/include/index/index.h
 */
class BruteForceIndex : public Index {
 public:
  explicit BruteForceIndex(std::shared_ptr<MemoryPool> memory_pool)
      : Index(std::move(memory_pool)) {}

  ~BruteForceIndex() override = default;

  // Prevent copying
  BruteForceIndex(const BruteForceIndex&) = delete;
  auto operator=(const BruteForceIndex&) -> BruteForceIndex& = delete;

  // Allow moving
  BruteForceIndex(BruteForceIndex&&) = default;
  auto operator=(BruteForceIndex&&) -> BruteForceIndex& = default;

  /**
   * @brief Initialize the brute force index
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
   * @brief Search for k nearest neighbors using brute force
   * @param query_vector Query vector
   * @param k Number of nearest neighbors to return
   * @return Vector of search results
   */
  auto Search(const std::vector<float>& query_vector, size_t k) const 
      -> std::vector<SearchResult> override;

  /**
   * @brief Build the index (no-op for brute force)
   * @return true always successful
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
   * @return IndexType::kBruteForce
   */
  auto GetType() const -> IndexType override;

 private:
  IndexConfig config_;
  std::unordered_map<uint64_t, std::vector<float>> vectors_;
  
  /**
   * @brief Calculate cosine similarity between two vectors
   * @param vec1 First vector
   * @param vec2 Second vector
   * @return Cosine similarity score
   */
  auto CalculateCosineSimilarity(const std::vector<float>& vec1, 
                                const std::vector<float>& vec2) const -> float;
  
  /**
   * @brief Calculate Euclidean distance between two vectors
   * @param vec1 First vector
   * @param vec2 Second vector
   * @return Euclidean distance
   */
  auto CalculateEuclideanDistance(const std::vector<float>& vec1, 
                                 const std::vector<float>& vec2) const -> float;
};

}  // namespace sage_flow
