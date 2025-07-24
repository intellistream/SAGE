#pragma once

#include <vector>
#include "index_operator.h"
#include "index_types.h"

namespace sage_flow {

class Index;

/**
 * @brief Interface for Top-K operators
 * Reference: flow_old/include/index/index.h
 */
class ITopKOperator : public IndexOperator {
 public:
  explicit ITopKOperator(std::shared_ptr<MemoryPool> memory_pool)
      : IndexOperator(std::move(memory_pool)) {}

  ~ITopKOperator() override = default;

  // Prevent copying
  ITopKOperator(const ITopKOperator&) = delete;
  auto operator=(const ITopKOperator&) -> ITopKOperator& = delete;

  // Allow moving
  ITopKOperator(ITopKOperator&&) = default;
  auto operator=(ITopKOperator&&) -> ITopKOperator& = default;

  /**
   * @brief Process Top-K operation
   * @param index The index to operate on
   * @return true if operation successful
   */
  auto Process(std::shared_ptr<Index> index) -> bool override = 0;

  /**
   * @brief Get operator type name
   * @return Operator type as string
   */
  auto GetOperatorType() const -> std::string override = 0;

  /**
   * @brief Configure the operator
   * @param config Configuration string
   * @return true if configuration successful
   */
  auto Configure(const std::string& config) -> bool override = 0;

  /**
   * @brief Set the number of top results to return
   * @param k Number of top results
   */
  virtual void SetTopK(size_t k) = 0;

  /**
   * @brief Get the current top-k value
   * @return Current k value
   */
  virtual auto GetTopK() const -> size_t = 0;

  /**
   * @brief Set query parameters
   * @param query_vector Query vector
   */
  virtual void SetQuery(const std::vector<float>& query_vector) = 0;

  /**
   * @brief Get top-k results
   * @return Vector of top results
   */
  virtual auto GetTopKResults() const -> std::vector<SearchResult> = 0;

  /**
   * @brief Set similarity threshold for filtering results
   * @param threshold Minimum similarity score
   */
  virtual void SetSimilarityThreshold(float threshold) = 0;

  /**
   * @brief Get current similarity threshold
   * @return Current threshold value
   */
  virtual auto GetSimilarityThreshold() const -> float = 0;
};

/**
 * @brief Concrete implementation of Top-K operator
 */
class TopKOperator : public ITopKOperator {
 public:
  explicit TopKOperator(std::shared_ptr<MemoryPool> memory_pool)
      : ITopKOperator(std::move(memory_pool)) {}

  ~TopKOperator() override = default;

  // Prevent copying
  TopKOperator(const TopKOperator&) = delete;
  auto operator=(const TopKOperator&) -> TopKOperator& = delete;

  // Allow moving
  TopKOperator(TopKOperator&&) = default;
  auto operator=(TopKOperator&&) -> TopKOperator& = default;

  /**
   * @brief Process Top-K search operation
   * @param index The index to search in
   * @return true if search successful
   */
  auto Process(std::shared_ptr<Index> index) -> bool override;

  /**
   * @brief Get operator type name
   * @return "TopKOperator"
   */
  auto GetOperatorType() const -> std::string override;

  /**
   * @brief Configure the Top-K operator
   * @param config Configuration string
   * @return true if configuration successful
   */
  auto Configure(const std::string& config) -> bool override;

  /**
   * @brief Set the number of top results to return
   * @param k Number of top results
   */
  void SetTopK(size_t k) override;

  /**
   * @brief Get the current top-k value
   * @return Current k value
   */
  auto GetTopK() const -> size_t override;

  /**
   * @brief Set query parameters
   * @param query_vector Query vector
   */
  void SetQuery(const std::vector<float>& query_vector) override;

  /**
   * @brief Get top-k results
   * @return Vector of top results
   */
  auto GetTopKResults() const -> std::vector<SearchResult> override;

  /**
   * @brief Set similarity threshold for filtering results
   * @param threshold Minimum similarity score
   */
  void SetSimilarityThreshold(float threshold) override;

  /**
   * @brief Get current similarity threshold
   * @return Current threshold value
   */
  auto GetSimilarityThreshold() const -> float override;

 private:
  size_t k_ = 10;
  float similarity_threshold_ = 0.0F;
  std::vector<float> query_vector_;
  std::vector<SearchResult> results_;
  
  /**
   * @brief Filter results by similarity threshold
   * @param results Results to filter
   * @return Filtered results
   */
  auto FilterBySimilarity(const std::vector<SearchResult>& results) const 
      -> std::vector<SearchResult>;
};

}  // namespace sage_flow
