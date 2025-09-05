#include "operator/sink_operator.hpp"

#include <stdexcept>
#include <utility>

#include "function/function.hpp"
#include "operator/response.hpp"

namespace sage_flow {

SinkOperator::SinkOperator(std::string name)
    : BaseOperator(OperatorType::kSink, std::move(name)),
      sink_function_(nullptr) {}

SinkOperator::SinkOperator(std::string name,
                           std::unique_ptr<SinkFunction> sink_function)
    : BaseOperator(OperatorType::kSink, std::move(name)),
      sink_function_(std::move(sink_function)) {}

auto SinkOperator::process(Response& input_record, int slot) -> bool {
  (void)slot;  // Suppress unused parameter warning

  if (!sink_function_) {
    throw std::runtime_error("SinkOperator: No SinkFunction set");
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

  // Execute the sink function (sink functions typically return empty response)
  sink_function_->execute(function_input);

  incrementProcessedCount();
  // Sink operators don't produce output, so no need to increment output count

  return true;
}

void SinkOperator::setSinkFunction(
    std::unique_ptr<SinkFunction> sink_function) {
  sink_function_ = std::move(sink_function);
}

auto SinkOperator::getSinkFunction() -> SinkFunction& {
  if (!sink_function_) {
    throw std::runtime_error("SinkOperator: No SinkFunction set");
  }
  return *sink_function_;
}

void SinkOperator::flush() {
  if (sink_function_) {
    sink_function_->close();  // SinkFunction's close() method handles flushing
  }
}

}  // namespace sage_flow
