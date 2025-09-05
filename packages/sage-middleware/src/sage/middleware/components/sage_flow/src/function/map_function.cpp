#include "function/map_function.hpp"

namespace sage_flow {

MapFunction::MapFunction(std::string name)
    : BaseFunction(std::move(name), FunctionType::Map) {}

MapFunction::MapFunction(std::string name, MapFunc map_func)
    : BaseFunction(std::move(name), FunctionType::Map),
      map_func_(std::move(map_func)) {}

auto MapFunction::execute(FunctionResponse& response) -> FunctionResponse {
  FunctionResponse result;

  // Apply map function to each message
  for (auto& message : response.getMessages()) {
    if (map_func_ && message) {
      // Apply the transformation function
      map_func_(message);
      result.addMessage(std::move(message));
    }
  }

  response.clear();
  return result;
}

void MapFunction::setMapFunc(MapFunc map_func) {
  map_func_ = std::move(map_func);
}

}  // namespace sage_flow
