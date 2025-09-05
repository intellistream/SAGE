#include "operator/filter_operator.hpp"

#include <stdexcept>
#include <utility>

#include "function/function.hpp"
#include "operator/response.hpp"

namespace sage_flow {

FilterOperator::FilterOperator(std::string name)
    : BaseOperator(OperatorType::kFilter, std::move(name)),
      filter_function_(nullptr) {}

FilterOperator::FilterOperator(std::string name,
                               std::unique_ptr<FilterFunction> filter_function)
    : BaseOperator(OperatorType::kFilter, std::move(name)),
      filter_function_(std::move(filter_function)) {}

auto FilterOperator::process(Response& input_record, int slot) -> bool {
  (void)slot;  // Suppress unused parameter warning

  if (!filter_function_) {
    throw std::runtime_error("FilterOperator: No FilterFunction set");
  }

  if (!input_record.hasMessage()) {
    return false;
  }

  auto input_message = input_record.getMessage();
  if (!input_message) {
    return false;
  }

  incrementProcessedCount();

  // Create FunctionResponse from input
  FunctionResponse function_input;
  function_input.addMessage(std::move(input_message));

  // Execute the filter function
  auto function_output = filter_function_->execute(function_input);

  // Filter functions return the message if it passes, empty response if it
  // doesn't
  bool has_output = false;
  auto& output_messages = function_output.getMessages();
  for (auto& output_message : output_messages) {
    if (output_message) {
      Response output_record(std::move(output_message));
      emit(0, output_record);
      incrementOutputCount();
      has_output = true;
    }
  }

  return has_output;
}

void FilterOperator::setFilterFunction(
    std::unique_ptr<FilterFunction> filter_function) {
  filter_function_ = std::move(filter_function);
}

auto FilterOperator::getFilterFunction() -> FilterFunction& {
  if (!filter_function_) {
    throw std::runtime_error("FilterOperator: No FilterFunction set");
  }
  return *filter_function_;
}

}  // namespace sage_flow
