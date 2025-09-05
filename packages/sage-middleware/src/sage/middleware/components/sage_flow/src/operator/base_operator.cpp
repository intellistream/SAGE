#include "../../include/operator/base_operator.hpp"

#include "../../include/operator/operator_types.hpp"

#include <iostream>

namespace sage_flow {

// Constructors
BaseOperator::BaseOperator(OperatorType type) : type_(type) {}

BaseOperator::BaseOperator(OperatorType type, std::string name)
    : type_(type), name_(std::move(name)) {}

// Virtual destructor is defined in header file

// Core operator interface - default implementations
auto BaseOperator::open() -> void {
  // Default implementation - do nothing
}

auto BaseOperator::close() -> void {
  // Default implementation - do nothing
}

auto BaseOperator::emit(int output_id, Response& output_record) const -> void {
  // If emit callback is set, use it to forward the message
  if (emit_callback_) {
    std::cout << "[BaseOperator] Emitting message with callback for operator " << name_ << std::endl;
    emit_callback_(output_id, output_record);
  } else {
    std::cout << "[BaseOperator] No emit callback set for operator " << name_ << std::endl;
  }
  // Otherwise, do nothing (backward compatibility)
}

// Accessors
auto BaseOperator::getType() const -> OperatorType { return type_; }

auto BaseOperator::getName() const -> const std::string& { return name_; }

auto BaseOperator::setName(std::string name) -> void {
  name_ = std::move(name);
}

// Performance monitoring
auto BaseOperator::getProcessedCount() const -> uint64_t {
  return processed_count_;
}

auto BaseOperator::getOutputCount() const -> uint64_t { return output_count_; }

auto BaseOperator::resetCounters() -> void {
  processed_count_ = 0;
  output_count_ = 0;
}

// Utility methods
auto BaseOperator::incrementProcessedCount() -> void { ++processed_count_; }

auto BaseOperator::incrementOutputCount() -> void { ++output_count_; }

// Emit callback management
auto BaseOperator::setEmitCallback(EmitCallback callback) -> void {
  emit_callback_ = std::move(callback);
}

auto BaseOperator::getEmitCallback() const -> const EmitCallback& {
  return emit_callback_;
}

}  // namespace sage_flow
