#pragma once

#include <memory>
#include <string>
#include <vector>
#include "index_types.h"

namespace sage_flow {

class MemoryPool;

/**
 * @brief Base class for all index types
 * Reference: flow_old/include/index/index.h
 */
class Index {
 public:
  explicit Index(std::shared_ptr<MemoryPool> memory_pool)
      : memory_pool_(std::move(memory_pool)) {}
  
  virtual ~Index() = default;

  // Prevent copying
  Index(const Index&) = delete;
  auto operator=(const Index&) -> Index& = delete;

  // Allow moving
  Index(Index&&) = default;
  auto operator=(Index&&) -> Index& = default;

  /**
   * @brief Initialize the index with configuration
   * @param config Index configuration parameters
   * @return true if initialization successful
   */
  virtual auto Initialize(const IndexConfig& config) -> bool = 0;

  /**
   * @brief Add vector to the index
   * @param id Unique identifier for the vector
   * @param vector Vector data
   * @return true if addition successful
   */
  virtual auto AddVector(uint64_t id, const std::vector<float>& vector) -> bool = 0;

  /**
   * @brief Search for k nearest neighbors
   * @param query_vector Query vector
   * @param k Number of nearest neighbors to return
   * @return Vector of search results
   */
  virtual auto Search(
      const std::vector<float>& query_vector, size_t k) const -> std::vector<SearchResult> = 0;

  /**
   * @brief Build the index after adding vectors
   * @return true if building successful
   */
  virtual auto Build() -> bool = 0;

  /**
   * @brief Save index to file
   * @param file_path Path to save the index
   * @return true if saving successful
   */
  virtual auto SaveIndex(const std::string& file_path) const -> bool = 0;

  /**
   * @brief Load index from file
   * @param file_path Path to load the index from
   * @return true if loading successful
   */
  virtual auto LoadIndex(const std::string& file_path) -> bool = 0;

  /**
   * @brief Get the current size of the index
   * @return Number of vectors in the index
   */
  virtual auto Size() const -> size_t = 0;

  /**
   * @brief Clear all data from the index
   */
  virtual void Clear() = 0;

  /**
   * @brief Get index type
   * @return Index type enum
   */
  virtual auto GetType() const -> IndexType = 0;

 protected:
  std::shared_ptr<MemoryPool> memory_pool_;
};

}  // namespace sage_flow
