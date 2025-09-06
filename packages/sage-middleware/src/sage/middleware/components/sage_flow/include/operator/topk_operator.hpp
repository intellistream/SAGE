#pragma once

#include <memory>
#include <string>
#include <vector>

#include "base_operator.hpp"
#include "response.hpp"

namespace sage_flow {

#include "message/multimodal_message.hpp"


using ResponseType = Response<MultiModalMessage>;

/**
 * @brief TopK operator for maintaining top-K results
 *
 * Maintains the top K elements based on a scoring function.
 * Useful for ranking and selection operations.
 */
class TopKOperator : public BaseOperator<MultiModalMessage, MultiModalMessage> {
public:
  explicit TopKOperator(std::string name, size_t k);

  // Prevent copying
  TopKOperator(const TopKOperator&) = delete;
  auto operator=(const TopKOperator&) -> TopKOperator& = delete;

  // Allow moving
  TopKOperator(TopKOperator&&) = default;
  auto operator=(TopKOperator&&) -> TopKOperator& = default;

  auto process(const std::vector<std::shared_ptr<MultiModalMessage>>& input) -> std::optional<ResponseType> override;

  // TopK-specific interface
  virtual auto getScore(const MultiModalMessage& message) -> float = 0;
  auto setK(size_t k) -> void;
  auto getK() const -> size_t;
  auto getTopK() const -> std::vector<std::shared_ptr<MultiModalMessage>>;

private:
  size_t k_;
  std::vector<std::shared_ptr<MultiModalMessage>> top_k_elements_;

  auto insertElement(std::shared_ptr<MultiModalMessage> message) -> void;
  auto maintainTopK() -> void;
};

}  // namespace sage_flow
