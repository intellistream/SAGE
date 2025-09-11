#include "function/map_function.hpp"

namespace sage_flow {

template <typename InType, typename OutType>
MapFunction<InType, OutType>::MapFunction(std::string name)
    : BaseFunction<InType, OutType>(std::move(name), FunctionType::map) {}

template <typename InType, typename OutType>
MapFunction<InType, OutType>::MapFunction(std::string name, MapFunc map_func)
    : BaseFunction<InType, OutType>(std::move(name), FunctionType::map),
      map_func_(std::move(map_func)) {}

template <typename InType, typename OutType>
void MapFunction<InType, OutType>::execute_batch(const std::vector<InType>& inputs, std::vector<OutType>& outputs) {
  for (const auto& input : inputs) {
    if (map_func_) {
      outputs.push_back(map_func_(input));
    } else {
      // Default identity function if no map_func provided
      outputs.push_back(static_cast<OutType>(input));
    }
  }
}

template <typename InType, typename OutType>
void MapFunction<InType, OutType>::setMapFunc(MapFunc map_func) {
  map_func_ = std::move(map_func);
}

// Explicit template instantiation for MultiModalMessage

}  // namespace sage_flow
