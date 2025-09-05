#include "operator/terminal_sink_operator.hpp"

#include <iostream>
#include <stdexcept>

#include "operator/operator_types.hpp"

namespace sage_flow {

TerminalSinkOperator::TerminalSinkOperator(SinkFunction sink_func)
    : BaseOperator(OperatorType::kSink, "TerminalSink"),
      sink_func_(std::move(sink_func)) {
  if (!sink_func_) {
    throw std::invalid_argument("SinkFunction cannot be null");
  }
}

auto TerminalSinkOperator::process(Response& input_record, int slot) -> bool {
  incrementProcessedCount();

  try {
    const auto& messages = input_record.getMessages();
    for (const auto& message_ptr : messages) {
      if (message_ptr) {
        sink_func_(*message_ptr);
      }
    }

    incrementOutputCount();
    return true;
  } catch (const std::exception& e) {
    // Log error and continue processing
    std::cerr << "TerminalSinkOperator error: " << e.what() << '\n';
    return false;
  }
}

auto TerminalSinkOperator::open() -> void { BaseOperator::open(); }

auto TerminalSinkOperator::close() -> void { BaseOperator::close(); }

// Factory function implementation
auto CreateTerminalSink(
    const std::function<void(const MultiModalMessage&)>& sink_func)
    -> std::unique_ptr<TerminalSinkOperator> {
  return std::make_unique<TerminalSinkOperator>(sink_func);
}

}  // namespace sage_flow
