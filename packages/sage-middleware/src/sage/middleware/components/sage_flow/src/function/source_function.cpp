#include "function/source_function.hpp"

namespace sage_flow {

template <typename OutType>
SourceFunction<OutType>::SourceFunction(std::string name)
    : BaseFunction<DummyInput, OutType>(std::move(name), FunctionType::source) {}

template <typename OutType>
std::optional<OutType> SourceFunction<OutType>::execute(const DummyInput& input) {
  if (hasNext()) {
    auto batch = generate_batch();
    if (!batch.empty()) {
      has_more_data_ = true;
      // For single execute, return first item if available
      return batch[0];
    }
  }
  has_more_data_ = false;
  return std::nullopt;
}

template <typename OutType>
void SourceFunction<OutType>::execute_batch(const std::vector<DummyInput>& inputs, std::vector<OutType>& outputs) {
  if (hasNext()) {
    auto batch = generate_batch();
    outputs = std::move(batch);
    if (outputs.empty()) {
      has_more_data_ = false;
    } else {
      has_more_data_ = true;
    }
  } else {
    // No more data, empty outputs
    outputs.clear();
  }
}


}  // namespace sage_flow