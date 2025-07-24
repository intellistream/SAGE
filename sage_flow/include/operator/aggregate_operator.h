#pragma once

#include <memory>
#include <string>
#include <unordered_map>
#include <vector>
#include "base_operator.h"

namespace sage_flow {

class MultiModalMessage;
class Response;

/**
 * @brief Aggregate operator for data aggregation
 * 
 * Performs aggregation operations (count, sum, avg, etc.) on groups of messages.
 * Supports windowed aggregation for streaming data.
 */
class AggregateOperator : public Operator {
 public:
  explicit AggregateOperator(std::string name);

  // Prevent copying
  AggregateOperator(const AggregateOperator&) = delete;
  auto operator=(const AggregateOperator&) -> AggregateOperator& = delete;

  // Allow moving
  AggregateOperator(AggregateOperator&&) = default;
  auto operator=(AggregateOperator&&) -> AggregateOperator& = default;
  
  auto process(Response& input_record, int slot) -> bool override;
  
  // Aggregate-specific interface
  virtual auto aggregate(std::vector<std::unique_ptr<MultiModalMessage>> inputs)
      -> std::unique_ptr<MultiModalMessage> = 0;
  virtual auto getGroupKey(const MultiModalMessage& message) -> std::string = 0;
  virtual auto shouldTriggerAggregation() -> bool = 0;
  
 private:
  // Internal state for aggregation
  std::unordered_map<std::string, std::vector<std::unique_ptr<MultiModalMessage>>> groups_;
  
  auto addToGroup(const std::string& key, std::unique_ptr<MultiModalMessage> message) -> void;
  auto processGroup(const std::string& key) -> void;
};

}  // namespace sage_flow
