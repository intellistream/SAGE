#pragma once

#include <functional>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>
#include <optional>

#include "base_operator.hpp"
#include "operator/response.hpp"
#include "message/multimodal_message.hpp"

namespace sage_flow {

class AggregateOperator : public BaseOperator<MultiModalMessage, MultiModalMessage> {
public:
  using KeyExtractor = std::function<std::string(const std::shared_ptr<MultiModalMessage>&)>;
  using AggregateFunc = std::function<std::shared_ptr<MultiModalMessage>(std::vector<std::shared_ptr<MultiModalMessage>>)>;
  
  AggregateOperator(std::string name, KeyExtractor key_ex, AggregateFunc agg_func, int window_size = 1);

  // Prevent copying
  AggregateOperator(const AggregateOperator&) = delete;
  auto operator=(const AggregateOperator&) -> AggregateOperator& = delete;

  // Allow moving
  AggregateOperator(AggregateOperator&&) = default;
  auto operator=(AggregateOperator&&) -> AggregateOperator& = default;

  auto process(const std::vector<std::shared_ptr<MultiModalMessage>>& input) -> std::optional<Response<MultiModalMessage>> override;

private:
  KeyExtractor key_extractor_;
  AggregateFunc aggregate_func_;
  int window_size_;
  std::unordered_map<std::string, std::vector<std::shared_ptr<MultiModalMessage>>> groups_;

  auto addToGroup(const std::string& key, std::shared_ptr<MultiModalMessage> message) -> void;
  auto processGroup(const std::string& key) -> void;
  auto shouldTriggerAggregation() -> bool;
};

}  // namespace sage_flow
