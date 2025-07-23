// Core operator types and enums
#include "operator/operator_types.h"

// Response container
#include "operator/response.h"

// Base operator class
#include "operator/base_operator.h"

// Specific operator implementations
#include "operator/source_operator.h"
#include "operator/map_operator.h"
#include "operator/filter_operator.h"
#include "operator/sink_operator.h"
#include "operator/join_operator.h"
#include "operator/aggregate_operator.h"
#include "operator/topk_operator.h"
#include "operator/window_operator.h"

#include <utility>
#include <algorithm>

namespace sage_flow {

// Response implementation
Response::Response(std::unique_ptr<MultiModalMessage> message) {
  messages_.emplace_back(std::move(message));
}

Response::Response(std::vector<std::unique_ptr<MultiModalMessage>> messages)
    : messages_(std::move(messages)) {}

Response::Response(Response&& other) noexcept
    : messages_(std::move(other.messages_)) {}

auto Response::operator=(Response&& other) noexcept -> Response& {
  if (this != &other) {
    messages_ = std::move(other.messages_);
  }
  return *this;
}

auto Response::hasMessage() const -> bool {
  return !messages_.empty();
}

auto Response::hasMessages() const -> bool {
  return messages_.size() > 1;
}

auto Response::getMessage() -> std::unique_ptr<MultiModalMessage> {
  if (messages_.empty()) {
    return nullptr;
  }
  auto result = std::move(messages_.front());
  messages_.erase(messages_.begin());
  return result;
}

auto Response::getMessages() -> std::vector<std::unique_ptr<MultiModalMessage>> {
  return std::move(messages_);
}

auto Response::size() const -> size_t {
  return messages_.size();
}

// Operator base class implementation
Operator::Operator(OperatorType type) 
    : type_(type) {}

Operator::Operator(OperatorType type, std::string name)
    : type_(type), name_(std::move(name)) {}

auto Operator::open() -> void {
  // Default implementation - can be overridden by derived classes
}

auto Operator::close() -> void {
  // Default implementation - can be overridden by derived classes
}

auto Operator::emit(int output_id, Response& output_record) const -> void {
  // Default implementation - emit to next operator in pipeline
  // This will be connected to the actual pipeline execution engine
  static_cast<void>(output_id);        // Suppress unused parameter warning
  static_cast<void>(output_record);    // Suppress unused parameter warning
}

auto Operator::getType() const -> OperatorType {
  return type_;
}

auto Operator::getName() const -> const std::string& {
  return name_;
}

auto Operator::setName(std::string name) -> void {
  name_ = std::move(name);
}

auto Operator::getProcessedCount() const -> uint64_t {
  return processed_count_;
}

auto Operator::getOutputCount() const -> uint64_t {
  return output_count_;
}

auto Operator::resetCounters() -> void {
  processed_count_ = 0;
  output_count_ = 0;
}

auto Operator::incrementProcessedCount() -> void {
  ++processed_count_;
}

auto Operator::incrementOutputCount() -> void {
  ++output_count_;
}

// SourceOperator implementation
SourceOperator::SourceOperator(std::string name)
    : Operator(OperatorType::kSource, std::move(name)) {}

auto SourceOperator::process(Response& input_record, int slot) -> bool {
  static_cast<void>(input_record);  // Suppress unused parameter warning
  static_cast<void>(slot);          // Suppress unused parameter warning
  
  if (hasNext()) {
    auto message = next();
    if (message) {
      Response output_response(std::move(message));
      emit(0, output_response);
      incrementProcessedCount();
      incrementOutputCount();
      return true;
    }
  }
  return false;
}

auto SourceOperator::runSource() -> void {
  while (hasNext()) {
    Response dummy_input(std::vector<std::unique_ptr<MultiModalMessage>>{});
    if (!process(dummy_input, 0)) {
      break;
    }
  }
}

// MapOperator implementation  
MapOperator::MapOperator(std::string name)
    : Operator(OperatorType::kMap, std::move(name)) {}

auto MapOperator::process(Response& input_record, int slot) -> bool {
  static_cast<void>(slot);  // Suppress unused parameter warning
  
  if (input_record.hasMessage()) {
    auto input_message = input_record.getMessage();
    if (input_message) {
      auto output_message = map(std::move(input_message));
      if (output_message) {
        Response output_response(std::move(output_message));
        emit(0, output_response);
        incrementProcessedCount();
        incrementOutputCount();
        return true;
      }
    }
  }
  return false;
}

// FilterOperator implementation
FilterOperator::FilterOperator(std::string name)
    : Operator(OperatorType::kFilter, std::move(name)) {}

auto FilterOperator::process(Response& input_record, int slot) -> bool {
  static_cast<void>(slot);  // Suppress unused parameter warning
  
  if (input_record.hasMessage()) {
    auto input_message = input_record.getMessage();
    if (input_message) {
      if (filter(*input_message)) {
        Response output_response(std::move(input_message));
        emit(0, output_response);
        incrementOutputCount();
      }
      incrementProcessedCount();
      return true;
    }
  }
  return false;
}

// SinkOperator implementation
SinkOperator::SinkOperator(std::string name)
    : Operator(OperatorType::kSink, std::move(name)) {}

auto SinkOperator::process(Response& input_record, int slot) -> bool {
  static_cast<void>(slot);  // Suppress unused parameter warning
  
  if (input_record.hasMessage()) {
    auto input_message = input_record.getMessage();
    if (input_message) {
      sink(std::move(input_message));
      incrementProcessedCount();
      return true;
    }
  }
  return false;
}

// JoinOperator implementation
JoinOperator::JoinOperator(std::string name)
    : Operator(OperatorType::kJoin, std::move(name)) {}

auto JoinOperator::process(Response& input_record, int slot) -> bool {
  if (input_record.hasMessage()) {
    auto input_message = input_record.getMessage();
    if (input_message) {
      if (slot == 0) {  // Left input
        processLeftInput(std::move(input_message));
      } else if (slot == 1) {  // Right input
        processRightInput(std::move(input_message));
      }
      incrementProcessedCount();
      return true;
    }
  }
  return false;
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
    auto joined_message = join(std::move(left_it->second), std::move(right_it->second));
    if (joined_message) {
      Response output_response(std::move(joined_message));
      emit(0, output_response);
      incrementOutputCount();
    }
    
    left_buffer_.erase(left_it);
    right_buffer_.erase(right_it);
  }
}

// AggregateOperator implementation
AggregateOperator::AggregateOperator(std::string name)
    : Operator(OperatorType::kAggregate, std::move(name)) {}

auto AggregateOperator::process(Response& input_record, int slot) -> bool {
  static_cast<void>(slot);  // Suppress unused parameter warning
  
  if (input_record.hasMessage()) {
    auto input_message = input_record.getMessage();
    if (input_message) {
      const std::string key = getGroupKey(*input_message);
      addToGroup(key, std::move(input_message));
      
      if (shouldTriggerAggregation()) {
        for (auto& [group_key, messages] : groups_) {
          processGroup(group_key);
        }
        groups_.clear();
      }
      
      incrementProcessedCount();
      return true;
    }
  }
  return false;
}

auto AggregateOperator::addToGroup(const std::string& key, std::unique_ptr<MultiModalMessage> message) -> void {
  groups_[key].emplace_back(std::move(message));
}

auto AggregateOperator::processGroup(const std::string& key) -> void {
  auto it = groups_.find(key);
  if (it != groups_.end() && !it->second.empty()) {
    auto aggregated_message = aggregate(std::move(it->second));
    if (aggregated_message) {
      Response output_response(std::move(aggregated_message));
      emit(0, output_response);
      incrementOutputCount();
    }
  }
}

// TopKOperator implementation
TopKOperator::TopKOperator(std::string name, size_t k)
    : Operator(OperatorType::kTopK, std::move(name)), k_(k) {}

auto TopKOperator::process(Response& input_record, int slot) -> bool {
  static_cast<void>(slot);  // Suppress unused parameter warning
  
  if (input_record.hasMessage()) {
    auto input_message = input_record.getMessage();
    if (input_message) {
      insertElement(std::move(input_message));
      incrementProcessedCount();
      return true;
    }
  }
  return false;
}

auto TopKOperator::setK(size_t k) -> void {
  k_ = k;
  maintainTopK();
}

auto TopKOperator::getK() const -> size_t {
  return k_;
}

auto TopKOperator::getTopK() const -> std::vector<std::unique_ptr<MultiModalMessage>> {
  std::vector<std::unique_ptr<MultiModalMessage>> result;
  // Note: This creates a copy, which breaks the unique_ptr semantics
  // In practice, you might want to return references or use a different approach
  return result;
}

auto TopKOperator::insertElement(std::unique_ptr<MultiModalMessage> message) -> void {
  top_k_elements_.emplace_back(std::move(message));
  maintainTopK();
}

auto TopKOperator::maintainTopK() -> void {
  if (top_k_elements_.size() <= k_) {
    return;
  }
  
  // Sort by score in descending order
  std::sort(top_k_elements_.begin(), top_k_elements_.end(),
            [this](const std::unique_ptr<MultiModalMessage>& a,
                   const std::unique_ptr<MultiModalMessage>& b) {
              return getScore(*a) > getScore(*b);
            });
  
  // Keep only top K elements
  top_k_elements_.resize(k_);
}

// WindowOperator implementation
WindowOperator::WindowOperator(std::string name, WindowType window_type)
    : Operator(OperatorType::kWindow, std::move(name)),
      window_type_(window_type),
      window_size_(std::chrono::seconds(10)),  // Default 10 seconds
      slide_interval_(std::chrono::seconds(5)), // Default 5 seconds
      window_start_time_(std::chrono::system_clock::now()) {}

auto WindowOperator::process(Response& input_record, int slot) -> bool {
  static_cast<void>(slot);  // Suppress unused parameter warning
  
  if (input_record.hasMessage()) {
    auto input_message = input_record.getMessage();
    if (input_message) {
      current_window_.emplace_back(std::move(input_message));
      
      if (shouldTriggerWindow()) {
        emitWindow();
      }
      
      incrementProcessedCount();
      return true;
    }
  }
  return false;
}

auto WindowOperator::setWindowSize(std::chrono::milliseconds size) -> void {
  window_size_ = size;
}

auto WindowOperator::setSlideInterval(std::chrono::milliseconds interval) -> void {
  slide_interval_ = interval;
}

auto WindowOperator::shouldTriggerWindow() -> bool {
  const auto now = std::chrono::system_clock::now();
  const auto elapsed = now - window_start_time_;
  
  switch (window_type_) {
    case WindowType::kTumbling:
      return elapsed >= window_size_;
    case WindowType::kSliding:
      return elapsed >= slide_interval_;
    case WindowType::kSession:
      // Session window logic would be more complex
      return elapsed >= window_size_;
    default:
      return false;
  }
}

auto WindowOperator::emitWindow() -> void {
  if (!current_window_.empty()) {
    auto processed_messages = processWindow(std::move(current_window_));
    for (auto& message : processed_messages) {
      Response output_response(std::move(message));
      emit(0, output_response);
      incrementOutputCount();
    }
  }
  resetWindow();
}

auto WindowOperator::resetWindow() -> void {
  current_window_.clear();
  window_start_time_ = std::chrono::system_clock::now();
}

}  // namespace sage_flow
