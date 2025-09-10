#include "operator/join_operator.hpp"
#include <utility>
#include <iostream>
#include <cassert>

namespace sage_flow {

JoinOperator::JoinOperator(std::string name, KeyExtractorLeft key_left, KeyExtractorRight key_right, JoinFunc join_func)
    : BaseOperator<MultiModalMessage, MultiModalMessage>(OperatorType::kJoin, std::move(name)), key_left_(std::move(key_left)), key_right_(std::move(key_right)), join_func_(std::move(join_func)), description_("") {}

JoinOperator::JoinOperator(std::string name, KeyExtractorLeft key_left, KeyExtractorRight key_right, JoinFunc join_func, std::string description)
    : BaseOperator<MultiModalMessage, MultiModalMessage>(OperatorType::kJoin, std::move(name), std::move(description)), key_left_(std::move(key_left)), key_right_(std::move(key_right)), join_func_(std::move(join_func)), description_(std::move(description)) {
  std::cout << "JoinOperator: Initialized with description: " << description_ << std::endl;
}

auto JoinOperator::process(const std::vector<std::shared_ptr<MultiModalMessage>>& input) -> std::optional<Response<MultiModalMessage>> {
  std::cout << "JoinOperator: Processing " << input.size() << " input messages" << std::endl;
  incrementProcessedCount();

  Response<MultiModalMessage> response;
  bool has_output = false;

  for (const auto& message_ptr : input) {
    if (message_ptr) {
      // Assume left input for simplicity; in real impl, distinguish left/right
      processLeftInput(message_ptr);
      // Check for joins and collect outputs
      // This is simplified; in full impl, would check buffers after each input
    }
  }

  // For now, return empty optional if no immediate output; real impl would trigger on matches
  // Placeholder: return optional with empty response
  if (has_output) {
    return std::make_optional(response);
  } else {
    return std::nullopt;
  }
}

auto JoinOperator::processLeftInput(const std::shared_ptr<MultiModalMessage>& message_ptr) -> void {
  assert(message_ptr != nullptr && "Null message in processLeftInput");
  std::cout << "JoinOperator: Processing left input with key: " << key_left_(message_ptr) << std::endl;
  KeyType key = key_left_(message_ptr);
  left_buffer_[key].push_back(message_ptr);
  tryJoin(key);
}

auto JoinOperator::processRightInput(const std::shared_ptr<MultiModalMessage>& message_ptr) -> void {
  assert(message_ptr != nullptr && "Null message in processRightInput");
  std::cout << "JoinOperator:: Processing right input with key: " << key_right_(message_ptr) << std::endl;
  KeyType key = key_right_(message_ptr);
  right_buffer_[key].push_back(message_ptr);
  tryJoin(key);
}

auto JoinOperator::tryJoin(const KeyType& key) -> void {
  auto left_it = left_buffer_.find(key);
  auto right_it = right_buffer_.find(key);

  if (left_it != left_buffer_.end() && !left_it->second.empty() && right_it != right_buffer_.end() && !right_it->second.empty()) {
    std::cout << "JoinOperator: Performing join for key: " << key << std::endl;
    // Perform join for first matching pair (basic implementation)
    const auto& left_ptr = left_it->second.front();
    const auto& right_ptr = right_it->second.front();

    auto result_ptr = join_func_(left_ptr, right_ptr);

    this->incrementOutputCount();
    Response<MultiModalMessage> response(std::vector<std::shared_ptr<MultiModalMessage>>{result_ptr});
    emit(0, response);

    // Remove consumed messages (basic, no window)
    left_buffer_.erase(left_it);
    right_buffer_.erase(right_it);
  }
}

}  // namespace sage_flow
