#include "operator/base_operator.h"

#include "operator/response.h"
#include <utility>

namespace sage_flow {

Operator::Operator(OperatorType type) 
    : type_(type), name_("unnamed_operator") {}

Operator::Operator(OperatorType type, std::string name)
    : type_(type), name_(std::move(name)) {}

auto Operator::open() -> void {
  // Default implementation - can be overridden by derived classes
}

auto Operator::close() -> void {
  // Default implementation - can be overridden by derived classes
}

auto Operator::emit(int output_id, Response& output_record) const -> void {
  // Default implementation - can be overridden by derived classes
  // This would typically forward to a downstream operator
  (void)output_id;     // Suppress unused parameter warning
  (void)output_record; // Suppress unused parameter warning
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

}  // namespace sage_flow
