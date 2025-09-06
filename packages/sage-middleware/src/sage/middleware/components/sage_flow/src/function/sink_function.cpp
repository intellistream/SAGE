#include "function/sink_function.hpp"
#include <memory>

namespace sage_flow {

auto SinkFunction::execute([[maybe_unused]] FunctionResponse& response) -> FunctionResponse {
  // TODO: Process messages from FunctionResponse
  // For now, return empty response as sink consumes messages
  return FunctionResponse();
}

void SinkFunction::setSinkFunc(SinkFunc sink_func) {
  sink_func_ = std::move(sink_func);
}

}  // namespace sage_flow
