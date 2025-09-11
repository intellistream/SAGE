#include "function/filter_function.hpp"

namespace sage_flow {

template <typename InType, typename OutType>
FilterFunction<InType, OutType>::FilterFunction(std::string name)
    : BaseFunction<InType, OutType>(std::move(name), FunctionType::filter) {}

template <typename InType, typename OutType>
FilterFunction<InType, OutType>::FilterFunction(std::string name, FilterFunc filter_func)
    : BaseFunction<InType, OutType>(std::move(name), FunctionType::filter),
      filter_func_(std::move(filter_func)) {}

template <typename InType, typename OutType>
std::optional<OutType> FilterFunction<InType, OutType>::execute(const InType& input) {
  if (!filter_func_ || filter_func_(input)) {
    // Message passes the filter
    return static_cast<OutType>(input);
  }
  // Message filtered out - return empty optional
  return std::nullopt;
}

template <typename InType, typename OutType>
void FilterFunction<InType, OutType>::execute_batch(const std::vector<InType>& inputs, std::vector<OutType>& outputs) {
  for (const auto& input : inputs) {
    if (!filter_func_ || filter_func_(input)) {
      // Message passes the filter
      outputs.push_back(static_cast<OutType>(input));
    }
    // Messages that don't pass are filtered out (not added to outputs)
  }
}

template <typename InType, typename OutType>
void FilterFunction<InType, OutType>::setFilterFunc(FilterFunc filter_func) {
  filter_func_ = std::move(filter_func);
}


}  // namespace sage_flow
