#include "operator/aggregate_operator.hpp"

#include <utility>
#include <optional>
#include <iostream>

#include "operator/response.hpp"
#include "message/multimodal_message.hpp"

namespace sage_flow {

using GroupMessages = std::unordered_map<std::string, std::vector<std::shared_ptr<MultiModalMessage>>>;

AggregateOperator::AggregateOperator(std::string name, KeyExtractor key_ex, AggregateFunc agg_func, int window_size)
    : BaseOperator<MultiModalMessage, MultiModalMessage>(OperatorType::kAggregate, std::move(name)), 
      key_extractor_(std::move(key_ex)), aggregate_func_(std::move(agg_func)), window_size_(window_size), groups_() {}

auto AggregateOperator::process(const std::vector<std::shared_ptr<MultiModalMessage>>& input) -> std::optional<Response<MultiModalMessage>> {
  if (input.empty()) {
    return BaseOperator<MultiModalMessage, MultiModalMessage>::createEmptyResponse();
  }

  try {
    for (const auto& input_message : input) {
      if (!input_message) continue;
      
      incrementProcessedCount();
      const std::string key = key_extractor_(input_message);
      addToGroup(key, input_message);

      if (shouldTriggerAggregation()) {
        for (const auto& group_pair : groups_) {
          processGroup(group_pair.first);
        }
      }
    }

    // For batch processing, we might want to trigger aggregation based on batch size
    if (input.size() >= static_cast<size_t>(window_size_)) {
      for (const auto& group_pair : groups_) {
        processGroup(group_pair.first);
      }
    }

    return std::nullopt; // Aggregation operators typically don't return immediate results
  } catch (const std::exception& e) {
    std::cerr << "[AggregateOperator] Error processing batch: " << e.what() << std::endl;
    return BaseOperator<MultiModalMessage, MultiModalMessage>::createEmptyResponse();
  }
}

auto AggregateOperator::addToGroup(const std::string& key, std::shared_ptr<MultiModalMessage> message) -> void {
  groups_[key].push_back(std::move(message));
}

auto AggregateOperator::processGroup(const std::string& key) -> void {
  auto group_it = groups_.find(key);
  if (group_it != groups_.end() && !group_it->second.empty()) {
    auto aggregated_message = aggregate_func_(group_it->second);

    if (aggregated_message) {
      std::vector<std::shared_ptr<MultiModalMessage>> output_messages;
      output_messages.emplace_back(aggregated_message);
      Response<MultiModalMessage> output_record(output_messages);
      emit(0, output_record);
      incrementOutputCount();
    }

    // Clear the processed group
    groups_.erase(group_it);
  }
}

auto AggregateOperator::shouldTriggerAggregation() -> bool {
  // Trigger if any group reaches window size
  for (const auto& group_pair : groups_) {
    if (group_pair.second.size() >= static_cast<size_t>(window_size_)) {
      return true;
    }
  }
  return false;
}

}  // namespace sage_flow
