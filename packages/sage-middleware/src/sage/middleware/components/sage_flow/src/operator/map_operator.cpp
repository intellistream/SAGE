#include "operator/map_operator.hpp"

#include <stdexcept>
#include <utility>

#include "function/function.hpp"
#include "operator/response.hpp"

namespace sage_flow {

MapOperator::MapOperator(std::string name)
    : BaseOperator(OperatorType::kMap, std::move(name)),
      map_function_(nullptr) {}

MapOperator::MapOperator(std::string name,
                         std::unique_ptr<MapFunction> map_function)
    : BaseOperator(OperatorType::kMap, std::move(name)),
      map_function_(std::move(map_function)) {}

auto MapOperator::process(Response& input_record, int slot) -> bool {
  (void)slot;  // Suppress unused parameter warning

  if (!map_function_) {
    throw std::runtime_error("MapOperator: No MapFunction set");
  }

  if (!input_record.hasMessage()) {
    return false;
  }

  auto input_message = input_record.getMessage();
  if (!input_message) {
    return false;
  }

  // Create FunctionResponse from input
  FunctionResponse function_input;
  function_input.addMessage(std::move(input_message));

  // Execute the map function
  auto function_output = map_function_->execute(function_input);

  // Process the output messages
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

  incrementProcessedCount();
  return has_output;
}

void MapOperator::setMapFunction(std::unique_ptr<MapFunction> map_function) {
  map_function_ = std::move(map_function);
}

auto MapOperator::getMapFunction() -> MapFunction& {
  if (!map_function_) {
    throw std::runtime_error("MapOperator: No MapFunction set");
  }
  return *map_function_;
}

}  // namespace sage_flow
