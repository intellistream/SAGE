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

auto SinkOperator::process(const std::vector<std::shared_ptr<MultiModalMessage>>& input) -> std::optional<Response<MultiModalMessage>> {
  if (!sink_function_) {
    throw std::runtime_error("SinkOperator: No SinkFunction set");
  }

  for (const auto& message : input) {
    if (message) {
      sink_function_->sink(*message);
    }
  }

  incrementProcessedCount();
  // Sink operators don't produce output
  return std::nullopt;
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
