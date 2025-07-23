#include "operator/join_operator.h"

#include "operator/response.h"
#include <utility>

namespace sage_flow {

JoinOperator::JoinOperator(std::string name)
    : Operator(OperatorType::kJoin, std::move(name)) {}

auto JoinOperator::process(Response& input_record, int slot) -> bool {
  if (!input_record.hasMessage()) {
    return false;
  }
  
  auto input_message = input_record.getMessage();
  if (!input_message) {
    return false;
  }
  
  incrementProcessedCount();
  
  // Determine which input stream this message came from
  if (slot == 0) {
    processLeftInput(std::move(input_message));
  } else if (slot == 1) {
    processRightInput(std::move(input_message));
  }
  
  return true;
}

auto JoinOperator::processLeftInput(std::unique_ptr<MultiModalMessage> message) -> void {
  const std::string key = getJoinKey(*message);
  left_buffer_[key] = std::move(message);
  tryJoin(key);
}

auto JoinOperator::processRightInput(std::unique_ptr<MultiModalMessage> message) -> void {
  const std::string key = getJoinKey(*message);
  right_buffer_[key] = std::move(message);
  tryJoin(key);
}

auto JoinOperator::tryJoin(const std::string& key) -> void {
  auto left_it = left_buffer_.find(key);
  auto right_it = right_buffer_.find(key);
  
  if (left_it != left_buffer_.end() && right_it != right_buffer_.end()) {
    // Both sides are available, perform join
    auto joined_message = join(std::move(left_it->second), std::move(right_it->second));
    
    if (joined_message) {
      Response output_record(std::move(joined_message));
      emit(0, output_record);
      incrementOutputCount();
    }
    
    // Remove consumed messages from buffers
    left_buffer_.erase(left_it);
    right_buffer_.erase(right_it);
  }
}

}  // namespace sage_flow
