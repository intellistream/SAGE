#include "function/sink_function.hpp"

namespace sage_flow {

template <typename InType>
SinkFunction<InType>::SinkFunction(std::string name)
    : BaseFunction<InType, InType>(std::move(name), FunctionType::sink) {}

template <typename InType>
SinkFunction<InType>::SinkFunction(std::string name, SinkFunc sink_func)
    : BaseFunction<InType, InType>(std::move(name), FunctionType::sink),
      sink_func_(std::move(sink_func)) {}

template <typename InType>
std::optional<InType> SinkFunction<InType>::execute(const InType& input) {
  sink(input);
  // Sink functions consume messages, return empty optional
  return std::nullopt;
}

template <typename InType>
void SinkFunction<InType>::execute_batch(const std::vector<InType>& inputs, std::vector<InType>& outputs) {
  for (const auto& input : inputs) {
    sink(input);
  }
  // Sink functions consume all messages, outputs remain empty
}

template <typename InType>
void SinkFunction<InType>::sink(const InType& message) {
  if (sink_func_) {
    sink_func_(message);
  }
  // Default sink behavior - can be overridden by derived classes
}

template <typename InType>
void SinkFunction<InType>::setSinkFunc(SinkFunc sink_func) {
  sink_func_ = std::move(sink_func);
}

// Explicit template instantiation for MultiModalMessage

}  // namespace sage_flow