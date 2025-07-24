#include "operator/aggregate_operator.h"

#include "operator/response.h"
#include <utility>

namespace sage_flow {

AggregateOperator::AggregateOperator(std::string name)
    : Operator(OperatorType::kAggregate, std::move(name)) {}

auto AggregateOperator::process(Response& input_record, int slot) -> bool {
  (void)slot; // Suppress unused parameter warning
  
  if (!input_record.hasMessage()) {
    return false;
  }
  
  auto input_message = input_record.getMessage();
  if (!input_message) {
    return false;
  }
  
  incrementProcessedCount();
  
  const std::string key = getGroupKey(*input_message);
  addToGroup(key, std::move(input_message));
  
  if (shouldTriggerAggregation()) {
    processGroup(key);
  }
  
  return true;
}

auto AggregateOperator::addToGroup(const std::string& key, 
                                  std::unique_ptr<MultiModalMessage> message) -> void {
  groups_[key].push_back(std::move(message));
}

auto AggregateOperator::processGroup(const std::string& key) -> void {
  auto group_it = groups_.find(key);
  if (group_it != groups_.end() && !group_it->second.empty()) {
    auto aggregated_message = aggregate(std::move(group_it->second));
    
    if (aggregated_message) {
      Response output_record(std::move(aggregated_message));
      emit(0, output_record);
      incrementOutputCount();
    }
    
    // Clear the processed group
    groups_.erase(group_it);
  }
}

}  // namespace sage_flow
