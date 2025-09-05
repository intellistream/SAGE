#include "function/sink_function.hpp"

namespace sage_flow {

auto SinkFunction::execute(FunctionResponse& response) -> FunctionResponse {
  // Process each message with the sink function
  for (const auto& message : response.getMessages()) {
    if (message && sink_func_) {
      sink_func_(*message);
    }
  }

  response.clear();

  // Sinks return empty responses as they consume messages
  return FunctionResponse{};
}

void SinkFunction::setSinkFunc(SinkFunc sink_func) {
  sink_func_ = std::move(sink_func);
}

}  // namespace sage_flow
