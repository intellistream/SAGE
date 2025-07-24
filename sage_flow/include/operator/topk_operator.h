#pragma once

#include <memory>
#include <string>
#include <vector>
#include "base_operator.h"

namespace sage_flow {

class MultiModalMessage;
class Response;

/**
 * @brief TopK operator for maintaining top-K results
 * 
 * Maintains the top K elements based on a scoring function.
 * Useful for ranking and selection operations.
 */
class TopKOperator : public Operator {
 public:
  explicit TopKOperator(std::string name, size_t k);

  // Prevent copying
  TopKOperator(const TopKOperator&) = delete;
  auto operator=(const TopKOperator&) -> TopKOperator& = delete;

  // Allow moving
  TopKOperator(TopKOperator&&) = default;
  auto operator=(TopKOperator&&) -> TopKOperator& = default;
  
  auto process(Response& input_record, int slot) -> bool override;
  
  // TopK-specific interface
  virtual auto getScore(const MultiModalMessage& message) -> float = 0;
  auto setK(size_t k) -> void;
  auto getK() const -> size_t;
  auto getTopK() const -> std::vector<std::unique_ptr<MultiModalMessage>>;
  
 private:
  size_t k_;
  std::vector<std::unique_ptr<MultiModalMessage>> top_k_elements_;
  
  auto insertElement(std::unique_ptr<MultiModalMessage> message) -> void;
  auto maintainTopK() -> void;
};

}  // namespace sage_flow
