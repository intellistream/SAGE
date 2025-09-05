#include "function/filter_function.hpp"

namespace sage_flow {

FilterFunction::FilterFunction(std::string name)
    : BaseFunction(std::move(name), FunctionType::Filter) {}

FilterFunction::FilterFunction(std::string name, FilterFunc filter_func)
    : BaseFunction(std::move(name), FunctionType::Filter),
      filter_func_(std::move(filter_func)) {}

auto FilterFunction::execute(FunctionResponse& response) -> FunctionResponse {
  FunctionResponse result;

  // Apply filter function to each message
  for (auto& message : response.getMessages()) {
    if (message && (!filter_func_ || filter_func_(*message))) {
      // Message passes the filter or no filter function is set
      result.addMessage(std::move(message));
    }
    // Messages that don't pass the filter are discarded
  }

  response.clear();
  return result;
}

void FilterFunction::setFilterFunc(FilterFunc filter_func) {
  filter_func_ = std::move(filter_func);
}

}  // namespace sage_flow
