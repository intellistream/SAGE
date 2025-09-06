#include <stdexcept>

#include "../../include/function/base_function.hpp"

namespace sage_flow {

BaseFunction::BaseFunction(std::string name, FunctionType type)
    : name_(std::move(name)), type_(type) {}

auto BaseFunction::getName() const -> const std::string& { return name_; }

auto BaseFunction::getType() const -> FunctionType { return type_; }

void BaseFunction::setName(const std::string& name) { name_ = name; }

void BaseFunction::setType(FunctionType type) { type_ = type; }

auto BaseFunction::execute(FunctionResponse& response) -> FunctionResponse {
  // Default implementation - pass through
  FunctionResponse result;
  for (auto& message : response.getMessages()) {
    result.addMessage(std::move(message));
  }
  response.clear();
  return result;
}

auto BaseFunction::execute(FunctionResponse& left,
                           FunctionResponse& right) -> FunctionResponse {
  (void)left;
  (void)right;
  // Default implementation for dual-input functions
  throw std::runtime_error("Dual-input execute not implemented for function: " +
                           name_);
}

}  // namespace sage_flow
