#include "operator/terminal_sink_operator.hpp"

#include <iostream>
#include <stdexcept>

#include "operator/operator_types.hpp"

namespace sage_flow {

TerminalSinkOperator::TerminalSinkOperator(SinkFunction sink_func)
    : BaseOperator<MultiModalMessage, MultiModalMessage>(OperatorType::kSink, "TerminalSink"),
      sink_func_(std::move(sink_func)) {
  if (!sink_func_) {
    throw std::invalid_argument("SinkFunction cannot be null");
  }
}

auto TerminalSinkOperator::process(const std::vector<std::shared_ptr<MultiModalMessage>>& input) -> std::optional<Response<MultiModalMessage>> override {
  for (const auto& message : input) {
    if (message) {
      this->incrementProcessedCount();
      sink_func_(*message);
  this->incrementOutputCount();
  return std::nullopt;
}

void TerminalSinkOperator::open() { BaseOperator::open(); }

void TerminalSinkOperator::close() { BaseOperator::close(); }

// Factory function implementation
auto CreateTerminalSink(
    const std::function<void(const MultiModalMessage&)>& sink_func)
    -> std::unique_ptr<TerminalSinkOperator> {
  return std::make_unique<TerminalSinkOperator>(sink_func);
}

}  // namespace sage_flow
