#pragma once

#include <vector>
#include "index_operator.h"
#include "index_types.h"

namespace sage_flow {

class Index;

/**
 * @brief K-Nearest Neighbors operator for vector search
 * Reference: flow_old/include/index/index.h
 */
class KnnOperator : public IndexOperator {
 public:
  explicit KnnOperator(std::shared_ptr<MemoryPool> memory_pool)
      : IndexOperator(std::move(memory_pool)) {}

  ~KnnOperator() override = default;

  // Prevent copying
  KnnOperator(const KnnOperator&) = delete;
  auto operator=(const KnnOperator&) -> KnnOperator& = delete;

  // Allow moving
  KnnOperator(KnnOperator&&) = default;
  auto operator=(KnnOperator&&) -> KnnOperator& = default;

  /**
   * @brief Process KNN search operation
   * @param index The index to search in
   * @return true if search successful
   */
  auto Process(std::shared_ptr<Index> index) -> bool override;

  /**
   * @brief Get operator type name
   * @return "KnnOperator"
   */
  auto GetOperatorType() const -> std::string override;

  /**
   * @brief Configure the KNN operator
   * @param config Configuration string (JSON format)
   * @return true if configuration successful
   */
  auto Configure(const std::string& config) -> bool override;

  /**
   * @brief Set query vector for search
   * @param query_vector Vector to search for
   */
  void SetQueryVector(const std::vector<float>& query_vector);

  /**
   * @brief Set number of nearest neighbors to find
   * @param k Number of neighbors
   */
  void SetK(size_t k);

  /**
   * @brief Get search results from last operation
   * @return Vector of search results
   */
  auto GetResults() const -> const std::vector<SearchResult>&;

  /**
   * @brief Clear previous results
   */
  void ClearResults();

 private:
  std::vector<float> query_vector_;
  size_t k_ = 10;
  std::vector<SearchResult> results_;
  
  /**
   * @brief Parse JSON configuration string
   * @param config JSON configuration
   * @return true if parsing successful
   */
  auto ParseConfig(const std::string& config) -> bool;
};

}  // namespace sage_flow
